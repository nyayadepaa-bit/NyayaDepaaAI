"""
pipeline/ingest.py
-------------------
Orchestrates the full ingestion pipeline:
    1. Build dataset from PDFs  (dataset_builder)
    2. Chunk with legal semantics (chunker)
    3. Embed + upsert to Pinecone (embedder)

Idempotent: detects new/changed PDFs via file hashing.

Usage:
    python -m pipeline.ingest
"""

import json
import hashlib
import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import PDF_DIR, DATA_DIR, DATASET_FILE, INGEST_HASH_FILE, CHUNK_SIZE, CHUNK_OVERLAP
from pipeline.dataset_builder import build_dataset
from pipeline.chunker import chunk_dataset
from pipeline.embedder import upsert_chunks, get_pinecone_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def compute_pdf_hashes(pdf_dir: Path) -> dict[str, str]:
    """Compute MD5 hash of each PDF for change detection."""
    hashes = {}
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        h = hashlib.md5(pdf.read_bytes()).hexdigest()
        hashes[pdf.name] = h
    return hashes


def load_previous_hashes() -> dict[str, str]:
    """Load previously ingested PDF hashes."""
    if INGEST_HASH_FILE.exists():
        with open(INGEST_HASH_FILE, "r") as f:
            return json.load(f)
    return {}


def save_hashes(hashes: dict[str, str]):
    """Save current PDF hashes."""
    INGEST_HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INGEST_HASH_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def detect_changes(pdf_dir: Path) -> tuple[bool, int, int]:
    """
    Compare current PDFs against previous ingestion.

    Returns:
        (has_changes, new_count, total_count)
    """
    current = compute_pdf_hashes(pdf_dir)
    previous = load_previous_hashes()

    new_files = set(current.keys()) - set(previous.keys())
    changed_files = {
        k for k in current.keys() & previous.keys()
        if current[k] != previous[k]
    }

    total_new = len(new_files) + len(changed_files)
    return total_new > 0, total_new, len(current)


def run_ingestion(force: bool = False):
    """
    Run the full ingestion pipeline.

    Args:
        force: If True, re-ingest everything regardless of hashes
    """
    logger.info("=" * 60)
    logger.info("  NyayaDepaaAI — Ingestion Pipeline")
    logger.info("=" * 60)

    # Step 0: Check for changes
    if not force:
        has_changes, new_count, total = detect_changes(PDF_DIR)
        if not has_changes:
            logger.info(f"No new PDFs detected ({total} already ingested). Skipping.")
            logger.info("Use --force to re-ingest everything.")
            return
        logger.info(f"Detected {new_count} new/changed PDFs out of {total} total")
    else:
        logger.info("Force mode: re-ingesting all PDFs")

    # Step 1: Build dataset
    logger.info("\n📄 Step 1/3: Building dataset from PDFs...")
    record_count = build_dataset(PDF_DIR, DATASET_FILE)
    if record_count == 0:
        logger.error("No records extracted. Check PDF directory.")
        return

    # Step 2: Load dataset and chunk
    logger.info("\n✂️  Step 2/3: Semantic chunking...")
    records = []
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    chunks = chunk_dataset(records, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if not chunks:
        logger.error("No chunks generated.")
        return

    # Log category distribution
    cat_counts = {}
    for c in chunks:
        cat = c["metadata"].get("legal_category", "general")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    logger.info("Category distribution:")
    for cat, count in sorted(cat_counts.items()):
        logger.info(f"  {cat}: {count} chunks")

    # Step 3: Embed + upsert
    logger.info("\n🔗 Step 3/3: Embedding + Pinecone upsert...")
    index = get_pinecone_index()
    counts = upsert_chunks(chunks, index)

    # Save hashes
    current_hashes = compute_pdf_hashes(PDF_DIR)
    save_hashes(current_hashes)

    # Summary
    total_vectors = sum(counts.values())
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ Ingestion Complete!")
    logger.info(f"  PDFs processed: {len(current_hashes)}")
    logger.info(f"  Dataset records: {record_count}")
    logger.info(f"  Chunks created: {len(chunks)}")
    logger.info(f"  Vectors upserted: {total_vectors}")
    logger.info(f"  Namespaces: {list(counts.keys())}")
    logger.info("=" * 60)

    # Verify
    try:
        stats = index.describe_index_stats()
        logger.info(f"Pinecone stats: {stats}")
    except Exception as e:
        logger.warning(f"Could not fetch stats: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NyayaDepaaAI Ingestion Pipeline")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion of all PDFs")
    args = parser.parse_args()
    run_ingestion(force=args.force)
