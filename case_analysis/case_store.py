"""
case_analysis/case_store.py
----------------------------
ChromaDB persistent vector store for legal cases.
Stores case embeddings with full metadata for retrieval.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import CASE_DB_PATH, CASE_COLLECTION_NAME

logger = logging.getLogger(__name__)

_client = None
_collection = None


def get_client():
    global _client
    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path=str(CASE_DB_PATH))
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=CASE_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def upsert_cases(cases: list[dict], embeddings: list[list[float]]):
    """
    Upsert cases with their embeddings into ChromaDB.

    Args:
        cases: List of case dicts (from legal_cases.json)
        embeddings: Parallel list of embedding vectors
    """
    collection = get_collection()

    ids = [c["case_id"] for c in cases]
    documents = [c.get("case_summary", "") + " " + c.get("situation", "") for c in cases]

    metadatas = []
    for c in cases:
        metadatas.append({
            "case_id": c["case_id"],
            "case_name": c["case_name"],
            "legal_area": c.get("legal_area", ""),
            "court": c.get("court", ""),
            "year": int(c.get("year", 2000)),
            "case_result": c.get("case_result", ""),
            "case_summary": c.get("case_summary", "")[:500],
            "situation": c.get("situation", "")[:500],
            "judgement_summary": c.get("judgement_summary", "")[:500],
            "case_laws": ", ".join(c.get("case_laws", [])),
            "keywords": ", ".join(c.get("keywords", [])),
            "court_weight": float(c.get("court_weight", 0.4)),
        })

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    logger.info(f"Upserted {len(ids)} cases into ChromaDB collection '{CASE_COLLECTION_NAME}'")


def query_cases(embedding: list[float], top_k: int = 10) -> list[dict]:
    """
    Query the ChromaDB collection for similar cases.

    Returns:
        List of dicts with metadata + distance score (0-1, lower = more similar)
    """
    collection = get_collection()
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, collection.count()),
        include=["metadatas", "distances", "documents"],
    )

    output = []
    if not results["ids"] or not results["ids"][0]:
        return output

    for i, case_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        # ChromaDB cosine distance: 0=identical, 2=opposite. Convert to similarity 0-1
        similarity = max(0.0, min(1.0, 1.0 - distance / 2.0))
        output.append({
            **meta,
            "similarity_score": round(similarity, 4),
        })

    output.sort(key=lambda x: x["similarity_score"], reverse=True)
    return output


def collection_count() -> int:
    """Return number of cases stored in the collection."""
    return get_collection().count()
