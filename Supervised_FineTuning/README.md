# Supervised Fine-Tuning (SFT)

## Purpose
Fine-tune the CPT model on three legal downstream tasks:
1. **Prediction** — Classify judgment as Allowed / Dismissed / Partially Allowed
2. **Explanation** — Predict judgment + generate legal reasoning
3. **Q&A** — Answer legal questions using document context

## Data Requirements

### For Prediction (Task 1)
Each example needs:
```json
{"facts": "The accused was arrested on charges of...", "label": "Allowed"}
```
Labels: `Allowed`, `Dismissed`, `Partially Allowed`

### For Explanation (Task 2)
Each example needs:
```json
{
  "facts": "...",
  "label": "Dismissed",
  "explanation": "The court dismissed the petition because..."
}
```

### For Q&A (Task 3)
Each example needs:
```json
{
  "context": "Section 436 CrPC states that...",
  "question": "Under what conditions can bail be granted?",
  "answer": "Bail can be granted when..."
}
```

## Generating Labels
If you don't have labeled data, you can:
1. **Manual annotation** — Annotate a subset of your PDFs
2. **Silver labels** — Use GPT-4 or Claude API to auto-generate labels from case text
3. **Public datasets** — Use Indian Legal Documents (ILD), ILDC, or similar

## Steps

### 1. Prepare labeled data
```bash
python utils/data_formatter.py --labeled_data path/to/your_labels.jsonl
```

### 2. Configure
Edit `sft_config.yaml`:
- Set `base_model_id` to your CPT output path
- Verify data file paths

### 3. Run fine-tuning
```bash
cd Supervised_FineTuning

# Task 1: Prediction
python run_sft_prediction.py --config sft_config.yaml

# Task 2: Prediction + Explanation
python run_sft_explanation.py --config sft_config.yaml

# Task 3: Q&A
python run_sft_qa.py --config sft_config.yaml
```

### 4. Outputs
- `outputs/sft_prediction/`
- `outputs/sft_explanation/`
- `outputs/sft_qa/`
