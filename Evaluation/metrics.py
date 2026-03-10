"""
Evaluation/metrics.py
----------------------
All evaluation metrics for LegalLlama3:
    - Prediction: Accuracy, F1, Precision, Recall
    - Explanation: ROUGE-1/2/L, BERTScore
    - QA: ROUGE-L, BERTScore, Exact Match
"""

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# ---- Prediction Metrics ----

def compute_classification_metrics(
    predictions: list[str],
    references: list[str],
    labels: Optional[list[str]] = None,
) -> dict:
    """Compute accuracy, macro F1, precision, recall for prediction task."""
    from sklearn.metrics import (
        accuracy_score, f1_score, precision_score, recall_score, classification_report
    )

    if labels is None:
        labels = sorted(set(references))

    acc = accuracy_score(references, predictions)
    f1  = f1_score(references, predictions, labels=labels, average="macro", zero_division=0)
    prec = precision_score(references, predictions, labels=labels, average="macro", zero_division=0)
    rec  = recall_score(references, predictions, labels=labels, average="macro", zero_division=0)

    report = classification_report(references, predictions, labels=labels, zero_division=0)

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(f1, 4),
        "macro_precision": round(prec, 4),
        "macro_recall": round(rec, 4),
        "classification_report": report,
    }


# ---- Generation Metrics (Explanation & QA) ----

def compute_rouge(predictions: list[str], references: list[str]) -> dict:
    """Compute ROUGE-1, ROUGE-2, ROUGE-L scores."""
    from rouge_score import rouge_scorer

    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    r1, r2, rl = [], [], []

    for pred, ref in zip(predictions, references):
        scores = scorer.score(ref, pred)
        r1.append(scores["rouge1"].fmeasure)
        r2.append(scores["rouge2"].fmeasure)
        rl.append(scores["rougeL"].fmeasure)

    return {
        "rouge1": round(np.mean(r1), 4),
        "rouge2": round(np.mean(r2), 4),
        "rougeL": round(np.mean(rl), 4),
    }


def compute_bertscore(
    predictions: list[str],
    references: list[str],
    lang: str = "en",
    model_type: str = "microsoft/deberta-xlarge-mnli",
) -> dict:
    """Compute BERTScore (precision, recall, F1)."""
    from bert_score import score as bert_score_fn

    P, R, F1 = bert_score_fn(
        predictions, references,
        lang=lang,
        model_type=model_type,
        verbose=False,
    )
    return {
        "bertscore_precision": round(P.mean().item(), 4),
        "bertscore_recall":    round(R.mean().item(), 4),
        "bertscore_f1":        round(F1.mean().item(), 4),
    }


def compute_exact_match(predictions: list[str], references: list[str]) -> dict:
    """Compute exact match (normalized)."""
    def normalize(s):
        return " ".join(s.lower().strip().split())

    em = sum(normalize(p) == normalize(r) for p, r in zip(predictions, references))
    return {"exact_match": round(em / len(predictions), 4)}


def compute_all_metrics(
    predictions: list[str],
    references: list[str],
    task: str = "qa",          # "prediction" | "explanation" | "qa"
    labels: Optional[list[str]] = None,
) -> dict:
    """Compute all relevant metrics for a given task."""
    all_metrics = {}

    if task == "prediction":
        all_metrics.update(compute_classification_metrics(predictions, references, labels))

    elif task in ("explanation", "qa"):
        all_metrics.update(compute_rouge(predictions, references))
        try:
            all_metrics.update(compute_bertscore(predictions, references))
        except Exception as e:
            logger.warning(f"BERTScore failed: {e}. Skipping.")
        if task == "qa":
            all_metrics.update(compute_exact_match(predictions, references))

    return all_metrics
