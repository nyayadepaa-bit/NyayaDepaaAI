"""
run_pipeline.py
----------------
One-click script to:
  STEP 1 → Extract all PDFs from /pdfs → data/legal_cases_pinecone.jsonl
  STEP 2 → Verify the JSONL (count records, show sample)
  STEP 3 → Ingest JSONL into Pinecone (domestic_violence namespace)

Usage:
  cd d:/LegalLlama3
  python data/run_pipeline.py

Add new PDFs to d:/LegalLlama3/pdfs/ and re-run this script anytime.
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, "d:/LegalLlama3")

JSONL = Path("d:/LegalLlama3/data/legal_cases_pinecone.jsonl")


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ─────────────────────────────────────────────────────────────
#  STEP 1 — EXTRACT
# ─────────────────────────────────────────────────────────────
separator("STEP 1: Extracting PDFs → JSONL")

from data.extract_pdf_cases import extract_full_text, parse_case, PINECONE_OUTPUT, JSON_OUTPUT, PDF_DIR
import json
from tqdm import tqdm

if not PDF_DIR.exists():
    print(f"❌ PDF directory not found: {PDF_DIR}")
    sys.exit(1)

seen_sizes, unique_pdfs = set(), []
for p in sorted(PDF_DIR.glob("*.pdf")):
    sz = p.stat().st_size
    if sz not in seen_sizes:
        seen_sizes.add(sz)
        unique_pdfs.append(p)

total_raw = len(list(PDF_DIR.glob("*.pdf")))
print(f"📁 Found {total_raw} PDFs → {len(unique_pdfs)} unique (deduped by file size)")

records = []
auto_dur = 0
t0 = time.time()
for idx, pdf_path in enumerate(tqdm(unique_pdfs, desc="  Extracting")):
    text = extract_full_text(pdf_path)
    if not text:
        print(f"  ⚠️  Skipped (no text): {pdf_path.name}")
        continue
    record = parse_case(text, pdf_path.name, idx)
    records.append(record)
    if "days total" in str(record["metadata"]["duration"]):
        auto_dur += 1

elapsed = time.time() - t0
print(f"\n✅ Extracted {len(records)} records in {elapsed:.1f}s")
print(f"   Auto-computed durations : {auto_dur}")
print(f"   Explicit durations found: {len(records) - auto_dur}")

# Write JSONL
with open(PINECONE_OUTPUT, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, indent=2, ensure_ascii=False) + "\n\n")
print(f"   JSONL saved → {PINECONE_OUTPUT}")

# Write JSON
with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(records, f, indent=2, ensure_ascii=False)
print(f"   JSON  saved → {JSON_OUTPUT}")


# ─────────────────────────────────────────────────────────────
#  STEP 2 — VERIFY
# ─────────────────────────────────────────────────────────────
separator("STEP 2: Verifying JSONL")

raw = JSONL.read_text(encoding="utf-8")
loaded = [json.loads(c) for c in raw.split("\n\n") if c.strip()]
print(f"📄 Records in JSONL : {len(loaded)}")
print(f"   Metadata fields  : {len(loaded[0]['metadata'])} per record")

r = loaded[0]
print(f"\n--- SAMPLE RECORD (first case) ---")
print(r["text"])
print(f"--- END SAMPLE ---")

# Duration breakdown
unknown  = sum(1 for x in loaded if x["metadata"]["duration"] == "Unknown")
computed = sum(1 for x in loaded if "days total" in str(x["metadata"]["duration"]))
explicit = len(loaded) - unknown - computed
print(f"\n   Duration breakdown:")
print(f"     Explicit in PDF : {explicit}")
print(f"     Auto-computed   : {computed}")
print(f"     Unknown         : {unknown}")


# ─────────────────────────────────────────────────────────────
#  STEP 3 — INGEST INTO PINECONE
# ─────────────────────────────────────────────────────────────
separator("STEP 3: Ingesting → Pinecone (namespace: domestic_violence)")

from data.ingest_to_pinecone import load_records, ingest, sanitize_meta, NAMESPACE, BATCH_SIZE
from pipeline.embedder import get_pinecone_index
from app.config import PINECONE_API_KEY, PINECONE_INDEX_NAME

if not PINECONE_API_KEY:
    print("❌ PINECONE_API_KEY not set in .env — skipping ingest.")
    sys.exit(1)

print(f"🔌 Connecting to Pinecone index '{PINECONE_INDEX_NAME}'…")
index = get_pinecone_index()

recs = load_records(JSONL)
print(f"📦 Ingesting {len(recs)} records in batches of {BATCH_SIZE}…")
t1 = time.time()
total_upserted = ingest(recs, index)
elapsed2 = time.time() - t1

print(f"\n✅ Ingestion complete in {elapsed2:.1f}s")
print(f"   Vectors upserted : {total_upserted}/{len(recs)}")
print(f"   Index            : {PINECONE_INDEX_NAME}")
print(f"   Namespace        : {NAMESPACE}")

separator("PIPELINE COMPLETE")
print(f"  Total time  : {(time.time()-t0):.1f}s")
print(f"  Cases ready : {total_upserted}")
print(f"  Chatbot RAG : ✅ Live (restart uvicorn if changes don't appear)")
print()
