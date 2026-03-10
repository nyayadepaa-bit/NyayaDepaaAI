# Continued PreTraining (CPT)

## Purpose
Continue pretraining LLaMA 3 on your legal PDF corpus. This enriches the model's understanding of legal terminology, case structures, citation patterns, and domain-specific reasoning before task-specific fine-tuning.

## What happens here
- Base LLaMA 3 learns from raw legal text via next-token prediction
- No labels needed — purely self-supervised
- Uses QLoRA for memory efficiency (runs on 24GB VRAM)

## Steps

### 1. Prepare data
```bash
cd ..
python utils/pdf_extractor.py          # extract text from PDFs
python utils/data_formatter.py         # build cpt_train.jsonl + cpt_validation.jsonl
```

### 2. Configure
Edit `cpt_config.yaml`:
- Set `base_model_id` (default: `meta-llama/Meta-Llama-3-8B`)
- Set `output_dir` for your environment
- Set `report_to: "none"` if you don't use W&B

### 3. Run
```bash
cd Continued_PreTraining
python run_cpt.py --config cpt_config.yaml
```

### 4. Output
Model saved to `outputs/cpt_model/` — use this path in `sft_config.yaml`

## Hardware Requirements
| Model | Min VRAM | Recommended |
|---|---|---|
| LLaMA 3 8B | 16GB (QLoRA) | 24GB A10G |
| LLaMA 3 70B | 40GB (QLoRA) | 80GB A100 |

## Estimated Time
- 8B model, ~10k pages, 3 epochs: ~8-12 hours on A100
