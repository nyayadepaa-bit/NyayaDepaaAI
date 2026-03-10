# Evaluation

## Metrics by Task

| Task | Metrics |
|---|---|
| Prediction | Accuracy, Macro-F1, Precision, Recall, Classification Report |
| Explanation | ROUGE-1, ROUGE-2, ROUGE-L, BERTScore (P/R/F1) |
| Q&A | ROUGE-L, BERTScore F1, Exact Match |

## Running Evaluation

```bash
cd Evaluation

# Evaluate all tasks
python evaluate.py --task all

# Evaluate one task
python evaluate.py --task prediction --model_path ../outputs/sft_prediction

# Limit samples (for quick testing)
python evaluate.py --task qa --max_samples 50

# Without RAG
python evaluate.py --task qa --no_rag
```

## Output
Results saved to `outputs/evaluation/eval_results_<timestamp>.json`

## Interpretation Guide

**Prediction Task:**
- Accuracy > 70%: Good baseline
- Macro-F1 > 0.65: Good (handles class imbalance)

**Explanation Task:**
- ROUGE-L > 0.30: Reasonable legal explanation quality
- BERTScore F1 > 0.85: Strong semantic similarity

**Q&A Task:**
- ROUGE-L > 0.40: Good answer coverage
- BERTScore F1 > 0.87: High semantic accuracy
