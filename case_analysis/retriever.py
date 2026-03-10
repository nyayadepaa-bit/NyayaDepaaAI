"""
case_analysis/retriever.py
---------------------------
Semantic similarity retrieval for legal cases.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from case_analysis.case_embedder import embed_text
from case_analysis.case_store import query_cases
from app.config import CASE_TOP_K

logger = logging.getLogger(__name__)


def retrieve_similar(
    user_description: str,
    top_k: int = None,
    legal_area_filter: str = None,
) -> list[dict]:
    """
    Retrieve the most similar legal cases for a given user description.

    Args:
        user_description: Free-text description of the user's legal case
        top_k: Number of cases to retrieve (default from config)
        legal_area_filter: Optional filter by legal area (e.g., 'Criminal Law')

    Returns:
        Ranked list of similar case dicts with similarity_score
    """
    top_k = top_k or CASE_TOP_K

    logger.info(f"Retrieving top-{top_k} similar cases for query: {user_description[:80]}...")

    # Embed the user's description
    embedding = embed_text(user_description)

    # Query ChromaDB
    results = query_cases(embedding, top_k=top_k * 2)

    # Optional filter
    if legal_area_filter:
        results = [r for r in results if r.get("legal_area", "").lower() == legal_area_filter.lower()]

    # Return top-k
    return results[:top_k]
