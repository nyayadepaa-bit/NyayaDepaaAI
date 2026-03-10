"""
utils/data_formatter.py
-----------------------
Converts raw extracted corpus (corpus.jsonl) into:
  - data/processed/cpt_dataset.jsonl      → for Continued PreTraining
  - data/processed/sft_prediction.jsonl   → for SFT Task 1: Prediction
  - data/processed/sft_explanation.jsonl  → for SFT Task 2: Prediction + Explanation
  - data/processed/sft_qa.jsonl           → for SFT Task 3: Q&A

IMPORTANT: The SFT datasets require labeled data (judgment + explanation).
If you only have raw PDFs, the CPT dataset is auto-generated.
For SFT, you need to either:
  (a) Manually annotate a subset of cases, OR
  (b) Use a larger model (GPT-4, Claude) to auto-generate labels (silver labels)
"""

import json
import random
import argparse
import logging
from pathlib import Path
from typing import Generator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================
PROCESSED_DIR = Path("../data/processed")
CORPUS_FILE   = PROCESSED_DIR / "corpus.jsonl"

CPT_MAX_TOKENS   = 2048   # Max tokens per CPT training example
SFT_MAX_TOKENS   = 4096   # Max tokens for SFT examples
TRAIN_SPLIT      = 0.9    # 90% train / 10% validation
RANDOM_SEED      = 42

# SFT Prompt Templates (LLaMA 3 chat format)
SYSTEM_PROMPT = "You are an expert legal AI assistant specialized in analyzing court judgments and legal documents."

PREDICTION_TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system}<|eot_id|><|start_header_id|>user<|end_header_id|>
Based on the following legal case facts, predict the court's judgment (Allowed / Dismissed / Partially Allowed):

CASE FACTS:
{facts}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
JUDGMENT: {label}<|eot_id|>"""

EXPLANATION_TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system}<|eot_id|><|start_header_id|>user<|end_header_id|>
Based on the following legal case facts, predict the court's judgment and provide a detailed legal explanation.

CASE FACTS:
{facts}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
JUDGMENT: {label}

EXPLANATION: {explanation}<|eot_id|>"""

QA_TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system}<|eot_id|><|start_header_id|>user<|end_header_id|>
LEGAL CONTEXT:
{context}

QUESTION: {question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
{answer}<|eot_id|>"""
# ============================================================


def load_corpus(path: Path) -> list[dict]:
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    logger.info(f"Loaded {len(data)} records from {path}")
    return data


def build_cpt_dataset(corpus: list[dict], output_path: Path):
    """
    For CPT: just raw text from each page, concatenated into chunks.
    No labels needed — purely self-supervised next-token prediction.
    """
    random.seed(RANDOM_SEED)
    random.shuffle(corpus)

    split_idx = int(len(corpus) * TRAIN_SPLIT)
    train_data = corpus[:split_idx]
    val_data   = corpus[split_idx:]

    for split, data in [("train", train_data), ("validation", val_data)]:
        out_file = output_path.parent / f"cpt_{split}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for record in data:
                f.write(json.dumps({"text": record["text"]}, ensure_ascii=False) + "\n")
        logger.info(f"CPT {split}: {len(data)} records → {out_file}")


def build_sft_prediction_dataset(labeled_data: list[dict], output_path: Path):
    """
    SFT Task 1 — Prediction only.

    labeled_data format:
    [{"facts": "...", "label": "Allowed/Dismissed/Partially Allowed"}, ...]

    ### REPLACE THIS FUNCTION WITH YOUR ACTUAL LABELED DATASET LOADER ###
    """
    random.seed(RANDOM_SEED)
    random.shuffle(labeled_data)
    split_idx = int(len(labeled_data) * TRAIN_SPLIT)

    for split, data in [("train", labeled_data[:split_idx]), ("validation", labeled_data[split_idx:])]:
        out_file = output_path.parent / f"sft_prediction_{split}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for ex in data:
                text = PREDICTION_TEMPLATE.format(
                    system=SYSTEM_PROMPT,
                    facts=ex["facts"][:3000],
                    label=ex["label"]
                )
                f.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
        logger.info(f"SFT Prediction {split}: {len(data)} records → {out_file}")


def build_sft_explanation_dataset(labeled_data: list[dict], output_path: Path):
    """
    SFT Task 2 — Prediction + Explanation.

    labeled_data format:
    [{"facts": "...", "label": "...", "explanation": "..."}, ...]

    ### REPLACE THIS FUNCTION WITH YOUR ACTUAL LABELED DATASET LOADER ###
    """
    random.seed(RANDOM_SEED)
    random.shuffle(labeled_data)
    split_idx = int(len(labeled_data) * TRAIN_SPLIT)

    for split, data in [("train", labeled_data[:split_idx]), ("validation", labeled_data[split_idx:])]:
        out_file = output_path.parent / f"sft_explanation_{split}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for ex in data:
                text = EXPLANATION_TEMPLATE.format(
                    system=SYSTEM_PROMPT,
                    facts=ex["facts"][:2500],
                    label=ex["label"],
                    explanation=ex["explanation"]
                )
                f.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
        logger.info(f"SFT Explanation {split}: {len(data)} records → {out_file}")


def build_sft_qa_dataset(qa_data: list[dict], output_path: Path):
    """
    SFT Task 3 — Q&A over legal documents.

    qa_data format:
    [{"context": "...", "question": "...", "answer": "..."}, ...]

    ### REPLACE THIS FUNCTION WITH YOUR ACTUAL QA DATASET LOADER ###
    """
    random.seed(RANDOM_SEED)
    random.shuffle(qa_data)
    split_idx = int(len(qa_data) * TRAIN_SPLIT)

    for split, data in [("train", qa_data[:split_idx]), ("validation", qa_data[split_idx:])]:
        out_file = output_path.parent / f"sft_qa_{split}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for ex in data:
                text = QA_TEMPLATE.format(
                    system=SYSTEM_PROMPT,
                    context=ex["context"][:2500],
                    question=ex["question"],
                    answer=ex["answer"]
                )
                f.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
        logger.info(f"SFT QA {split}: {len(data)} records → {out_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=str, default=str(CORPUS_FILE))
    parser.add_argument("--output_dir", type=str, default=str(PROCESSED_DIR))
    parser.add_argument(
        "--labeled_data",
        type=str,
        default=None,
        help="Path to your labeled JSONL (required for SFT tasks). "
             "### PROVIDE YOUR LABELED DATA FILE PATH ###"
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build CPT dataset from raw corpus
    corpus = load_corpus(Path(args.corpus))
    build_cpt_dataset(corpus, output_dir / "cpt.jsonl")

    # 2. Build SFT datasets from labeled data
    if args.labeled_data:
        labeled = []
        with open(args.labeled_data, "r") as f:
            for line in f:
                labeled.append(json.loads(line))

        # Assumes your labeled data has both label+explanation+qa fields
        prediction_data = [x for x in labeled if "label" in x]
        explanation_data = [x for x in labeled if "label" in x and "explanation" in x]
        qa_data = [x for x in labeled if "question" in x and "answer" in x]

        if prediction_data:
            build_sft_prediction_dataset(prediction_data, output_dir / "sft_prediction.jsonl")
        if explanation_data:
            build_sft_explanation_dataset(explanation_data, output_dir / "sft_explanation.jsonl")
        if qa_data:
            build_sft_qa_dataset(qa_data, output_dir / "sft_qa.jsonl")
    else:
        logger.warning(
            "No --labeled_data provided. Only CPT dataset built.\n"
            "For SFT tasks, provide a labeled JSONL file."
        )

    logger.info("Data formatting complete.")


if __name__ == "__main__":
    main()
