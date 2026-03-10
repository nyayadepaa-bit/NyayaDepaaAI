"""
case_analysis/ingest_cases.py
------------------------------
Ingestion pipeline: loads legal_cases.json, embeds each case, upserts to ChromaDB.

Usage:
    python -m case_analysis.ingest_cases
    python -m case_analysis.ingest_cases --force
"""

import json
import logging
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import CASE_DATASET_FILE
from case_analysis.case_embedder import build_case_embedding_text, embed_batch
from case_analysis.case_store import upsert_cases, collection_count, get_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def assign_court_weights(cases: list[dict]) -> list[dict]:
    """Assign court_weight to each case based on court level."""
    from case_analysis.predictor import get_court_weight
    for case in cases:
        case["court_weight"] = get_court_weight(case.get("court", ""))
    return cases


def run_ingestion(force: bool = False):
    logger.info("=" * 60)
    logger.info("  Legal Case Analysis — Ingestion Pipeline")
    logger.info("=" * 60)

    # Check if already ingested
    if not force:
        count = collection_count()
        if count > 0:
            logger.info(f"ChromaDB already contains {count} cases. Use --force to re-ingest.")
            return count

    # Load dataset
    dataset_path = Path(CASE_DATASET_FILE)
    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}")
        logger.error("Run the dataset generator first: python data/generate_legal_cases.py")
        return 0

    logger.info(f"Loading cases from: {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    logger.info(f"Loaded {len(cases)} cases")

    # If force, reset collection
    if force:
        import chromadb
        from app.config import CASE_DB_PATH, CASE_COLLECTION_NAME
        client = chromadb.PersistentClient(path=str(CASE_DB_PATH))
        try:
            client.delete_collection(CASE_COLLECTION_NAME)
            logger.info(f"Deleted existing collection '{CASE_COLLECTION_NAME}'")
        except Exception:
            pass
        # Reset module-level cached collection
        import case_analysis.case_store as cs
        cs._collection = None
        cs._client = None

    # Assign court weights
    cases = assign_court_weights(cases)

    # Build embedding texts
    logger.info("Building embedding texts...")
    embedding_texts = [build_case_embedding_text(c) for c in cases]

    # Embed in batches
    logger.info(f"Embedding {len(cases)} cases (batch size 32)...")
    embeddings = embed_batch(embedding_texts)
    logger.info(f"Generated {len(embeddings)} embeddings")

    # Upsert to ChromaDB
    logger.info("Upserting to ChromaDB...")
    upsert_cases(cases, embeddings)

    final_count = collection_count()
    logger.info("=" * 60)
    logger.info(f"  Ingestion Complete! {final_count} cases stored.")
    logger.info("=" * 60)
    return final_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Legal Case Ingestion Pipeline")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion even if DB already has data")
    args = parser.parse_args()
    run_ingestion(force=args.force)
