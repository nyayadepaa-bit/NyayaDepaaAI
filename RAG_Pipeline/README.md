# RAG Pipeline (Pinecone)

## Architecture
```
Query → Embed (BGE-large) → Pinecone Search → Rerank (CrossEncoder) → Top-K Chunks → LLM
```

## Embedding Model
Uses `BAAI/bge-large-en-v1.5` (1024-dim) — state-of-the-art for retrieval, especially on legal/technical text.

## Steps

### 1. Set up Pinecone
- Create a free account at https://app.pinecone.io
- Create an API key
- Add to `.env`: `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`

### 2. Ingest PDFs into Pinecone
```bash
cd RAG_Pipeline
python ingest.py
```
This will:
- Load preprocessed corpus from `data/processed/corpus.jsonl`
- Split into 512-token chunks with 64-token overlap
- Embed with BGE-large
- Upsert all vectors into Pinecone

### 3. Run inference
```bash
# Q&A mode
python rag_inference.py --mode qa --query "What are the grounds for anticipatory bail?"

# Prediction mode
python rag_inference.py --mode prediction --facts "Accused was arrested under IPC 420..."

# Explanation mode
python rag_inference.py --mode explanation --facts "..."

# Without RAG (model knowledge only)
python rag_inference.py --mode qa --query "..." --no_rag
```

## Chunking Strategy
| Parameter | Value | Reason |
|---|---|---|
| Chunk size | 512 tokens | Fits legal sentence structures |
| Overlap | 64 tokens | Preserves cross-sentence context |
| Splitter | Recursive | Respects paragraph/sentence boundaries |

## Reranking
Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` to rerank top-10 Pinecone results → top-5 final.
Disable by setting `USE_RERANKER = False` in `retriever.py`.
