"""
RAG_Pipeline/ingest.py
-----------------------
Chunks your legal PDFs, generates embeddings, and upserts into Pinecone.

Pipeline:
    PDFs → Text Extraction → Chunking → Embedding → Pinecone Upsert

Usage:
    python ingest.py

Prerequisites:
    - Fill PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME in .env
    - Run utils/pdf_extractor.py first (or point directly to raw PDFs)
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from tqdm import tqdm
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG — adjust chunking strategy here
# ============================================================
CORPUS_FILE     = Path("../data/processed/corpus.jsonl")  # output of pdf_extractor.py
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"                # state-of-the-art for legal text
EMBEDDING_DIM   = 1024                                     # bge-large dimension

CHUNK_SIZE      = 512    # tokens per chunk
CHUNK_OVERLAP   = 64     # overlap between consecutive chunks
BATCH_SIZE      = 100    # upsert batch size to Pinecone

# Pinecone settings
PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "legal-llama-index")
# ============================================================


def get_pinecone_index():
    """Initialize Pinecone and create index if it doesn't exist."""
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not set. ### ADD IT TO YOUR .env FILE ###")

    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        logger.info(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",           # ### CHANGE TO YOUR CLOUD PROVIDER IF NEEDED ###
                region="us-east-1"     # ### CHANGE TO YOUR REGION IF NEEDED ###
            )
        )
    else:
        logger.info(f"Using existing Pinecone index: {PINECONE_INDEX_NAME}")

    return pc.Index(PINECONE_INDEX_NAME)


def load_corpus(path: Path) -> list[dict]:
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line.strip()))
    logger.info(f"Loaded {len(data)} pages from corpus")
    return data


def chunk_documents(corpus: list[dict]) -> list[dict]:
    """Split document pages into overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = []
    for doc in corpus:
        text = doc["text"]
        splits = splitter.split_text(text)
        for i, chunk_text in enumerate(splits):
            chunk_id = hashlib.md5(f"{doc['source']}_{doc['page']}_{i}".encode()).hexdigest()
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    "source": doc["source"],
                    "page": doc["page"],
                    "chunk_index": i,
                    "total_chunks": len(splits),
                }
            })

    logger.info(f"Created {len(chunks)} chunks from {len(corpus)} pages")
    return chunks


def batch_upsert(index, chunks: list[dict], embedder: SentenceTransformer):
    """Embed chunks in batches and upsert to Pinecone."""
    total_upserted = 0

    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Upserting to Pinecone"):
        batch = chunks[i: i + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        embeddings = embedder.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,  # normalize for cosine similarity
        )

        vectors = [
            {
                "id": c["id"],
                "values": emb.tolist(),
                "metadata": {**c["metadata"], "text": c["text"]},  # store text in metadata for retrieval
            }
            for c, emb in zip(batch, embeddings)
        ]

        index.upsert(vectors=vectors)
        total_upserted += len(vectors)

    logger.info(f"Total upserted: {total_upserted} vectors")


def main():
    # Load corpus
    if not CORPUS_FILE.exists():
        raise FileNotFoundError(
            f"Corpus not found at {CORPUS_FILE}. "
            "Run utils/pdf_extractor.py first."
        )

    corpus = load_corpus(CORPUS_FILE)
    chunks = chunk_documents(corpus)

    # Save chunk metadata locally for reference
    meta_file = Path("../data/embeddings/chunk_metadata.jsonl")
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_file, "w") as f:
        for c in chunks:
            f.write(json.dumps({"id": c["id"], "metadata": c["metadata"]}) + "\n")
    logger.info(f"Saved chunk metadata to {meta_file}")

    # Load embedding model
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    # Initialize Pinecone
    index = get_pinecone_index()

    # Embed + upsert
    logger.info("Starting embedding and Pinecone upsert...")
    batch_upsert(index, chunks, embedder)

    # Verify
    stats = index.describe_index_stats()
    logger.info(f"Pinecone index stats: {stats}")
    logger.info("Ingestion complete!")


if __name__ == "__main__":
    main()
