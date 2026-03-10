"""
case_analysis/case_embedder.py
-------------------------------
Embedding generation for legal cases using Jina AI.
Reuses the same Jina API key as the main pipeline.
"""

import logging
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import JINA_API_KEY, JINA_MODEL

logger = logging.getLogger(__name__)

JINA_EMBED_URL = "https://api.jina.ai/v1/embeddings"


def embed_text(text: str) -> list[float]:
    """Embed a single text string using Jina AI."""
    return embed_batch([text])[0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of text strings using Jina AI.
    Processes in batches of 32 to avoid rate limits.
    """
    if not texts:
        return []

    BATCH_SIZE = 32
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        try:
            headers = {
                "Authorization": f"Bearer {JINA_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": JINA_MODEL,
                "input": batch,
            }
            resp = requests.post(JINA_EMBED_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(embeddings)
            logger.info(f"Embedded batch {i // BATCH_SIZE + 1}: {len(batch)} texts")
        except Exception as e:
            logger.error(f"Embedding failed for batch starting at {i}: {e}")
            raise

    return all_embeddings


def build_case_embedding_text(case: dict) -> str:
    """
    Build the text string to embed for a legal case.
    Combines: case_name + case_summary + situation + judgement_summary
    """
    parts = [
        case.get("case_name", ""),
        f"Legal area: {case.get('legal_area', '')}",
        f"Summary: {case.get('case_summary', '')}",
        f"Situation: {case.get('situation', '')}",
        f"Judgement: {case.get('judgement_summary', '')}",
        f"Result: {case.get('case_result', '')}",
        f"Keywords: {', '.join(case.get('keywords', []))}",
    ]
    return " | ".join(p for p in parts if p.strip())
