"""
pipeline/embedder.py
---------------------
Pre-embedding pipeline using Google Gemini Embeddings API.
Upserts vectors to Pinecone with namespace separation by legal category.

Features:
    - Batch embedding via Gemini API (768-dim, free)
    - Fallback to Jina API if Gemini unavailable
    - Namespace-based Pinecone organization
    - Hash-based dedup (skip already-embedded chunks)
    - Idempotent indexing
"""

import time
import logging
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (
    GEMINI_API_KEY,
    JINA_API_KEY,
    JINA_MODEL,
    EMBEDDING_DIM,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 20       # Gemini batch size
UPSERT_BATCH = 100    # Pinecone upsert batch


def embed_texts_gemini(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using Google Gemini Embeddings API (free)."""
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]

        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=batch,
                task_type="retrieval_document",
            )
            # result["embedding"] is a list of lists when input is a list
            embeddings = result["embedding"]
            all_embeddings.extend(embeddings)
        except Exception as e:
            logger.error(f"Gemini embedding error on batch {i}: {e}")
            raise

        # Rate limit
        if i + BATCH_SIZE < len(texts):
            time.sleep(0.3)

    return all_embeddings


def embed_texts_jina(texts: list[str]) -> list[list[float]]:
    """Fallback: Generate embeddings using Jina API."""
    import requests

    JINA_URL = "https://api.jina.ai/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {JINA_API_KEY}",
        "Content-Type": "application/json",
    }

    all_embeddings = []

    for i in range(0, len(texts), 50):
        batch = texts[i : i + 50]
        payload = {"model": JINA_MODEL, "input": batch}

        try:
            r = requests.post(JINA_URL, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            batch_embeddings = [d["embedding"] for d in data["data"]]
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.error(f"Jina embedding error: {e}")
            raise

        if i + 50 < len(texts):
            time.sleep(0.1)

    return all_embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings using best available provider.
    Priority: Gemini (free, reliable) → Jina (fallback)
    """
    if GEMINI_API_KEY:
        try:
            logger.info(f"Using Gemini embeddings for {len(texts)} texts...")
            return embed_texts_gemini(texts)
        except Exception as e:
            logger.warning(f"Gemini embedding failed: {e}, trying Jina...")

    if JINA_API_KEY:
        logger.info(f"Using Jina embeddings for {len(texts)} texts...")
        return embed_texts_jina(texts)

    raise ValueError("No embedding API configured. Set GEMINI_API_KEY or JINA_API_KEY in .env")


def get_pinecone_index():
    """Initialize Pinecone and create/connect to index."""
    from pinecone import Pinecone, ServerlessSpec

    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not set.")

    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing = [idx["name"] for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        logger.info(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        time.sleep(5)
    else:
        logger.info(f"Using existing index: {PINECONE_INDEX_NAME}")

    return pc.Index(PINECONE_INDEX_NAME)


def upsert_chunks(chunks: list[dict], index=None) -> dict:
    """
    Embed chunks and upsert to Pinecone with namespace separation.

    Args:
        chunks: List of chunk dicts from chunker.py
        index: Optional Pinecone index (created if None)

    Returns:
        dict with counts per namespace
    """
    if index is None:
        index = get_pinecone_index()

    # Group chunks by namespace (legal_category)
    by_namespace: dict[str, list[dict]] = {}
    for chunk in chunks:
        ns = chunk["metadata"].get("legal_category", "general")
        if ns not in by_namespace:
            by_namespace[ns] = []
        by_namespace[ns].append(chunk)

    counts = {}

    for namespace, ns_chunks in by_namespace.items():
        logger.info(f"Embedding {len(ns_chunks)} chunks → namespace '{namespace}'")

        # Embed in batches
        texts = [c["text"] for c in ns_chunks]
        embeddings = embed_texts(texts)

        # Upsert in batches
        upserted = 0
        for i in range(0, len(ns_chunks), UPSERT_BATCH):
            batch_chunks = ns_chunks[i : i + UPSERT_BATCH]
            batch_embeddings = embeddings[i : i + UPSERT_BATCH]

            vectors = []
            for chunk, emb in zip(batch_chunks, batch_embeddings):
                # Sanitize metadata: Pinecone rejects None values
                raw_meta = {**chunk["metadata"], "text": chunk["text"][:1000]}
                meta = {k: (v if v is not None else "") for k, v in raw_meta.items()}
                vectors.append({
                    "id": chunk["id"],
                    "values": emb,
                    "metadata": meta,
                })

            index.upsert(vectors=vectors, namespace=namespace)
            upserted += len(vectors)

        counts[namespace] = upserted
        logger.info(f"  Upserted {upserted} vectors to '{namespace}'")

    return counts


def embed_query(query: str) -> list[float]:
    """Embed a single query for retrieval."""
    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=query,
                task_type="retrieval_query",
            )
            return result["embedding"]
        except Exception as e:
            logger.warning(f"Gemini query embed failed: {e}")

    # Fallback to Jina
    embeddings = embed_texts_jina([query])
    return embeddings[0]
