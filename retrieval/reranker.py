"""
retrieval/reranker.py
----------------------
Cross-encoder re-ranking for retrieval results.

Uses cross-encoder/ms-marco-MiniLM-L-6-v2 (lightweight, fast).
Falls back to score-based ranking if model unavailable.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_reranker = None


def _get_reranker():
    """Lazy-load the cross-encoder model."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("Cross-encoder reranker loaded")
        except Exception as e:
            logger.warning(f"Could not load reranker: {e}. Using score-based ranking.")
            _reranker = "unavailable"
    return _reranker if _reranker != "unavailable" else None


def rerank(query: str, results: list[dict], top_k: int = 4) -> list[dict]:
    """
    Re-rank results using cross-encoder.

    Args:
        query: Original user query
        results: List of retrieved result dicts (must have 'text' key)
        top_k: Number of results to return

    Returns:
        Re-ranked and filtered results
    """
    if not results:
        return []

    if len(results) <= top_k:
        return results

    reranker = _get_reranker()

    if reranker is None:
        # Fallback: just use existing scores
        return results[:top_k]

    try:
        pairs = [(query, r["text"]) for r in results]
        scores = reranker.predict(pairs)

        for r, score in zip(results, scores):
            r["rerank_score"] = float(score)

        reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]

    except Exception as e:
        logger.warning(f"Reranking failed: {e}. Using original order.")
        return results[:top_k]
