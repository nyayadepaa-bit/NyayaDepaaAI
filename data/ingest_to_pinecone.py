"""
data/ingest_to_pinecone.py
---------------------------
Reads legal_cases_pinecone.jsonl and upserts all records into Pinecone
under the 'domestic_violence' namespace.

Uses the same Gemini embedding model as the rest of the pipeline
(models/text-embedding-004, 768-dim) so queries hit the same vector space.

Run:
  python data/ingest_to_pinecone.py

Options (env vars):
  PINECONE_NAMESPACE  override namespace (default: domestic_violence)
  BATCH_SIZE          upsert batch size  (default: 50)
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

JSONL_FILE = Path("d:/LegalLlama3/data/legal_cases_pinecone.jsonl")
NAMESPACE  = os.getenv("PINECONE_NAMESPACE", "domestic_violence")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))

from app.config import PINECONE_API_KEY, PINECONE_INDEX_NAME, GEMINI_API_KEY, JINA_API_KEY, EMBEDDING_DIM
from pipeline.embedder import embed_texts, get_pinecone_index


def load_records(path: Path) -> list[dict]:
    """Load all JSON records from the pretty-printed JSONL file."""
    records = []
    raw = path.read_text(encoding="utf-8")
    # Split on blank lines — each record is one pretty-printed JSON object
    for chunk in raw.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            records.append(json.loads(chunk))
        except json.JSONDecodeError as e:
            logger.warning(f"  Skipped malformed chunk: {e}")
    return records


def sanitize_meta(meta: dict) -> dict:
    """
    Pinecone only accepts str | int | float | bool | list[str] values.
    Convert any None to '' and any unexpected types to str.
    """
    clean = {}
    for k, v in meta.items():
        if v is None:
            clean[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif isinstance(v, list):
            clean[k] = [str(i) for i in v]
        else:
            clean[k] = str(v)
    return clean


def ingest(records: list[dict], index) -> int:
    """Embed texts and upsert to Pinecone in batches. Returns total upserted."""
    total = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        texts = [r["text"] for r in batch]

        logger.info(f"  Embedding batch {i // BATCH_SIZE + 1} ({len(texts)} records)…")
        try:
            embeddings = embed_texts(texts)
        except Exception as e:
            logger.error(f"  Embedding failed for batch {i}: {e}")
            continue

        vectors = []
        for rec, emb in zip(batch, embeddings):
            meta = sanitize_meta({**rec["metadata"], "text": rec["text"][:2000]})
            vectors.append({"id": rec["id"], "values": emb, "metadata": meta})

        try:
            index.upsert(vectors=vectors, namespace=NAMESPACE)
            total += len(vectors)
            logger.info(f"  ✅ Upserted {len(vectors)} vectors (total so far: {total})")
        except Exception as e:
            logger.error(f"  Upsert failed for batch {i}: {e}")

        # Small pause to respect API rate limits
        if i + BATCH_SIZE < len(records):
            time.sleep(0.5)

    return total


def main():
    if not JSONL_FILE.exists():
        logger.error(f"JSONL file not found: {JSONL_FILE}")
        logger.error("Run `python data/extract_pdf_cases.py` first.")
        sys.exit(1)

    if not PINECONE_API_KEY:
        logger.error("PINECONE_API_KEY not set in .env")
        sys.exit(1)

    if not (GEMINI_API_KEY or JINA_API_KEY):
        logger.error("No embedding API key set. Need GEMINI_API_KEY or JINA_API_KEY in .env")
        sys.exit(1)

    logger.info(f"Loading records from {JSONL_FILE}…")
    records = load_records(JSONL_FILE)
    logger.info(f"Loaded {len(records)} case records.")

    logger.info(f"Connecting to Pinecone index '{PINECONE_INDEX_NAME}'…")
    index = get_pinecone_index()

    logger.info(f"Ingesting into namespace='{NAMESPACE}' in batches of {BATCH_SIZE}…")
    total = ingest(records, index)

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Ingestion complete — {total}/{len(records)} vectors upserted")
    logger.info(f"   Index   : {PINECONE_INDEX_NAME}")
    logger.info(f"   Namespace: {NAMESPACE}")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    main()
