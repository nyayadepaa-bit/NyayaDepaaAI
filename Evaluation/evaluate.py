"""
Evaluation/evaluate.py
-----------------------
Runs evaluation on all three tasks using the fine-tuned models.
Produces a comprehensive report with all metrics.

Usage:
    python evaluate.py --task prediction --model_path ../outputs/sft_prediction
    python evaluate.py --task explanation --model_path ../outputs/sft_explanation
    python evaluate.py --task qa --model_path ../outputs/sft_qa
    python evaluate.py --task all  # evaluates all tasks

Prerequisites:
    - Models must be trained
    - Test datasets must exist in data/processed/
    - Pinecone must be populated (for RAG evaluation)
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

import torch
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

sys.path.insert(0, str(Path(__file__).parent))
from metrics import compute_all_metrics

sys.path.insert(0, str(Path(__file__).parent.parent / "RAG_Pipeline"))
from retriever import LegalRetriever

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN")
MAX_NEW_TOKENS = 256

TASK_CONFIG = {
    "prediction": {
        "test_file": "../data/processed/sft_prediction_validation.jsonl",
        "model_path": "../outputs/sft_prediction",
        "labels": ["Allowed", "Dismissed", "Partially Allowed"],
    },
    "explanation": {
        "test_file": "../data/processed/sft_explanation_validation.jsonl",
        "model_path": "../outputs/sft_explanation",
    },
    "qa": {
        "test_file": "../data/processed/sft_qa_validation.jsonl",
        "model_path": "../outputs/sft_qa",
    },
}


def load_model(model_path: str):
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_path, token=HF_TOKEN, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=bnb_config,
        device_map="auto",
        token=HF_TOKEN,
        trust_remote_code=True,
    )
    model.eval()
    return model, tokenizer


def load_test_data(test_file: str, max_samples: int = 200) -> list[dict]:
    """Load test examples from JSONL."""
    data = []
    with open(test_file) as f:
        for line in f:
            data.append(json.loads(line))
    return data[:max_samples]


def extract_input_and_reference(item: dict, task: str) -> tuple[str, str]:
    """Parse input/reference from a formatted example."""
    text = item.get("text", "")
    # Extract from between user/assistant headers
    user_part   = text.split("<|start_header_id|>user<|end_header_id|>")[-1]
    user_part   = user_part.split("<|eot_id|>")[0].strip()
    asst_part   = text.split("<|start_header_id|>assistant<|end_header_id|>")[-1]
    asst_part   = asst_part.split("<|eot_id|>")[0].strip()
    return user_part, asst_part


def generate_prediction(model, tokenizer, prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=3500)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=0.1,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = out[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def evaluate_task(
    task: str,
    model_path: str,
    test_file: str,
    max_samples: int = 100,
    use_rag: bool = True,
) -> dict:
    logger.info(f"\n{'='*50}\nEvaluating task: {task.upper()}\n{'='*50}")
    cfg = TASK_CONFIG[task]

    if not Path(model_path).exists():
        logger.error(f"Model not found: {model_path}. ### TRAIN THE MODEL FIRST ###")
        return {}
    if not Path(test_file).exists():
        logger.error(f"Test file not found: {test_file}. ### PREPARE TEST DATA FIRST ###")
        return {}

    logger.info(f"Loading model from {model_path}...")
    model, tokenizer = load_model(model_path)

    retriever = None
    if use_rag:
        try:
            retriever = LegalRetriever()
        except Exception as e:
            logger.warning(f"RAG disabled: {e}")

    test_data = load_test_data(test_file, max_samples)
    logger.info(f"Evaluating on {len(test_data)} examples...")

    predictions, references = [], []

    for item in tqdm(test_data, desc=f"Eval {task}"):
        user_input, reference = extract_input_and_reference(item, task)

        # Optionally inject RAG context
        rag_ctx = ""
        if retriever:
            try:
                chunks = retriever.retrieve(user_input[:500])
                rag_ctx = retriever.format_context(chunks, max_chars=1500)
                rag_ctx = f"RELEVANT LEGAL CONTEXT:\n{rag_ctx}\n\n"
            except:
                pass

        prompt = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
            f"You are an expert legal AI assistant.<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n"
            f"{rag_ctx}{user_input}"
            f"<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
        )

        pred = generate_prediction(model, tokenizer, prompt)
        predictions.append(pred)
        references.append(reference)

    labels = cfg.get("labels")
    metrics = compute_all_metrics(predictions, references, task=task, labels=labels)

    logger.info(f"\nResults for {task.upper()}:")
    for k, v in metrics.items():
        if k != "classification_report":
            logger.info(f"  {k}: {v}")
    if "classification_report" in metrics:
        logger.info(f"\n{metrics['classification_report']}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate LegalLlama3")
    parser.add_argument("--task", choices=["prediction", "explanation", "qa", "all"], default="all")
    parser.add_argument("--model_path", type=str, default=None, help="Override model path")
    parser.add_argument("--test_file",  type=str, default=None, help="Override test file")
    parser.add_argument("--max_samples", type=int, default=100)
    parser.add_argument("--no_rag", action="store_true")
    args = parser.parse_args()

    tasks = list(TASK_CONFIG.keys()) if args.task == "all" else [args.task]
    all_results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for task in tasks:
        cfg = TASK_CONFIG[task]
        model_path = args.model_path or cfg["model_path"]
        test_file  = args.test_file  or cfg["test_file"]

        metrics = evaluate_task(
            task=task,
            model_path=model_path,
            test_file=test_file,
            max_samples=args.max_samples,
            use_rag=not args.no_rag,
        )
        all_results[task] = metrics

    # Save results
    output_dir = Path("../outputs/evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    results_file = output_dir / f"eval_results_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    logger.info(f"\nAll results saved to {results_file}")

    # Print summary table
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    for task, metrics in all_results.items():
        print(f"\n[{task.upper()}]")
        for k, v in metrics.items():
            if k != "classification_report":
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
