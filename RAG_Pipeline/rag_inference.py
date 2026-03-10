"""
RAG_Pipeline/rag_inference.py
------------------------------
Full RAG + Fine-tuned LLaMA 3 inference pipeline.

Supports three inference modes:
    1. prediction     — Predict judgment given case facts
    2. explanation    — Predict + explain the judgment
    3. qa             — Answer a legal question using retrieved context

Usage:
    python rag_inference.py --query "What are the grounds for bail?" --mode qa
    python rag_inference.py --facts "Accused was arrested for theft..." --mode prediction
    python rag_inference.py --facts "..." --mode explanation

Prerequisites:
    - Pinecone index must be populated (run ingest.py)
    - SFT models must be trained (or use base LLaMA 3 from CPT)
    - Fill model paths in .env or pass via CLI
"""

import os
import sys
import argparse
import logging
from pathlib import Path

import torch
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
from peft import PeftModel

sys.path.insert(0, str(Path(__file__).parent))
from retriever import LegalRetriever

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG — set your model paths here OR in .env
# ============================================================
DEFAULT_MODEL_PATHS = {
    "prediction":  os.getenv("SFT_PREDICTION_PATH",  "../outputs/sft_prediction"),
    "explanation": os.getenv("SFT_EXPLANATION_PATH", "../outputs/sft_explanation"),
    "qa":          os.getenv("SFT_QA_PATH",          "../outputs/sft_qa"),
}
HF_TOKEN = os.getenv("HF_TOKEN")
MAX_NEW_TOKENS = 512
TEMPERATURE    = 0.1    # low for factual/legal tasks
# ============================================================

SYSTEM_PROMPT = "You are an expert legal AI assistant specialized in analyzing court judgments and legal documents."

PROMPT_TEMPLATES = {
    "prediction": (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        "{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
        "{rag_context}"
        "Based on the following legal case facts, predict the court's judgment "
        "(Allowed / Dismissed / Partially Allowed):\n\nCASE FACTS:\n{input}"
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\nJUDGMENT:"
    ),
    "explanation": (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        "{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
        "{rag_context}"
        "Based on the following legal case facts, predict the court's judgment and "
        "provide a detailed legal explanation.\n\nCASE FACTS:\n{input}"
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\nJUDGMENT:"
    ),
    "qa": (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        "{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
        "LEGAL CONTEXT FROM DOCUMENTS:\n{rag_context}\n\n"
        "QUESTION: {input}"
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
    ),
}


class LegalLlamaRAG:
    def __init__(self, mode: str = "qa", model_path: str = None):
        self.mode = mode
        model_path = model_path or DEFAULT_MODEL_PATHS[mode]

        if not model_path or not Path(model_path).exists():
            raise ValueError(
                f"Model path not found: {model_path}. "
                f"### SET MODEL PATH IN .env OR PASS --model_path ###"
            )

        logger.info(f"Loading tokenizer from {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True, token=HF_TOKEN
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        logger.info(f"Loading model from {model_path} (4-bit quantization)")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            token=HF_TOKEN,
        )
        self.model.eval()

        logger.info("Initializing retriever...")
        self.retriever = LegalRetriever()
        logger.info("LegalLlamaRAG ready.")

    def generate(
        self,
        user_input: str,
        use_rag: bool = True,
        verbose: bool = True,
    ) -> dict:
        rag_context = ""

        if use_rag:
            logger.info("Retrieving relevant context from Pinecone...")
            retrieved = self.retriever.retrieve(user_input)
            rag_context = self.retriever.format_context(retrieved)
            if verbose:
                logger.info(f"Retrieved {len(retrieved)} chunks")

        prompt = PROMPT_TEMPLATES[self.mode].format(
            system=SYSTEM_PROMPT,
            rag_context=f"RELEVANT LEGAL CONTEXT:\n{rag_context}\n\n" if rag_context else "",
            input=user_input,
        )

        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=TEMPERATURE,
                do_sample=TEMPERATURE > 0,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        return {
            "query": user_input,
            "mode": self.mode,
            "response": response,
            "context_used": rag_context[:500] + "..." if rag_context else None,
        }


def main():
    parser = argparse.ArgumentParser(description="LegalLlama3 RAG Inference")
    parser.add_argument("--mode", choices=["prediction", "explanation", "qa"], default="qa",
                        help="Inference mode")
    parser.add_argument("--query", type=str, default=None, help="For QA mode: your legal question")
    parser.add_argument("--facts", type=str, default=None, help="For prediction/explanation: case facts")
    parser.add_argument("--model_path", type=str, default=None, help="Override model path")
    parser.add_argument("--no_rag", action="store_true", help="Disable RAG (use model knowledge only)")
    args = parser.parse_args()

    user_input = args.query or args.facts
    if not user_input:
        print("Please provide --query (for QA) or --facts (for prediction/explanation)")
        sys.exit(1)

    rag = LegalLlamaRAG(mode=args.mode, model_path=args.model_path)
    result = rag.generate(user_input, use_rag=not args.no_rag, verbose=True)

    print("\n" + "="*60)
    print(f"MODE: {result['mode'].upper()}")
    print(f"QUERY: {result['query'][:200]}")
    print("="*60)
    print(f"RESPONSE:\n{result['response']}")
    print("="*60)


if __name__ == "__main__":
    main()
