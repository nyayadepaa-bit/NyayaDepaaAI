# LegalLlama3 — Legal LLM with RAG Pipeline

A full pipeline for training, fine-tuning, and deploying a domain-specific Legal LLM based on **LLaMA 3**, with Pinecone RAG integration. Inspired by INLegalLlama.

---

## Architecture Overview

```
PDFs → Preprocessing → CPT → SFT → RAG (Pinecone) → Evaluation
```

| Phase | Description |
|---|---|
| **1. Continued PreTraining (CPT)** | Further pretrain LLaMA 3 on your legal PDFs corpus |
| **2. Supervised FineTuning (SFT)** | Fine-tune for 3 tasks: Prediction, Prediction+Explanation, Q&A |
| **3. RAG Pipeline** | Chunk PDFs → Embed → Store in Pinecone → Retrieve at inference |
| **4. Evaluation** | ROUGE, BERTScore, Accuracy, F1, legal-specific metrics |

---

## Folder Structure

```
LegalLlama3/
├── README.md
├── requirements.txt
├── .env.example
│
├── data/
│   ├── raw_pdfs/          ← Place your PDFs here
│   ├── processed/         ← Auto-generated preprocessed data
│   └── embeddings/        ← Cached embedding metadata
│
├── utils/
│   ├── pdf_extractor.py   ← Extract text from PDFs
│   └── data_formatter.py  ← Format datasets for CPT/SFT
│
├── Continued_PreTraining/
│   ├── README.md
│   ├── cpt_config.yaml
│   └── run_cpt.py
│
├── Supervised_FineTuning/
│   ├── README.md
│   ├── sft_config.yaml
│   ├── run_sft_prediction.py
│   ├── run_sft_explanation.py
│   └── run_sft_qa.py
│
├── RAG_Pipeline/
│   ├── README.md
│   ├── ingest.py          ← Chunk + embed + upsert to Pinecone
│   ├── retriever.py       ← Query Pinecone + rerank
│   └── rag_inference.py   ← Full RAG + LLM inference
│
└── Evaluation/
    ├── README.md
    ├── evaluate.py
    └── metrics.py
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables
```bash
cp .env.example .env
# Fill in your Pinecone API key, HuggingFace token, etc.
```

### 3. Place PDFs
```bash
cp your_legal_pdfs/*.pdf data/raw_pdfs/
```

### 4. Extract & preprocess PDFs
```bash
python utils/pdf_extractor.py
python utils/data_formatter.py
```

### 5. Run Continued PreTraining
```bash
cd Continued_PreTraining
python run_cpt.py --config cpt_config.yaml
```

### 6. Run Supervised Fine-Tuning
```bash
cd Supervised_FineTuning
python run_sft_prediction.py --config sft_config.yaml
python run_sft_explanation.py --config sft_config.yaml
python run_sft_qa.py --config sft_config.yaml
```

### 7. Ingest PDFs into Pinecone (RAG)
```bash
cd RAG_Pipeline
python ingest.py
```

### 8. Run inference with RAG
```bash
python RAG_Pipeline/rag_inference.py --query "What are the legal precedents for bail in India?"
```

### 9. Evaluate
```bash
python Evaluation/evaluate.py --model_path ### PATH_TO_YOUR_MODEL ###
```

---

## Important Notes

- Fill all `### PLACEHOLDERS ###` in config files before running
- Minimum GPU: 24GB VRAM for 8B model with QLoRA; 40GB+ for full fine-tune
- Recommended: A100 80GB or 2x A6000 for CPT
- All scripts support `--help` flag
