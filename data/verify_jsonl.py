import json
from pathlib import Path

path = Path("d:/LegalLlama3/data/legal_cases_pinecone.jsonl")
raw = path.read_text(encoding="utf-8")
records = [json.loads(c) for c in raw.split("\n\n") if c.strip()]
print(f"Total records: {len(records)}")

r = records[0]
print("=== SAMPLE TEXT BLOCK ===")
print(r["text"])
print()
print("=== METADATA KEYS ===")
print(list(r["metadata"].keys()))
print(f"Total metadata keys: {len(r['metadata'])}")
print()

auto    = sum(1 for rec in records if "days total" in str(rec["metadata"]["duration"]))
unknown = sum(1 for rec in records if rec["metadata"]["duration"] == "Unknown")
explicit = len(records) - auto - unknown
print(f"Duration breakdown: explicit={explicit}  auto-computed={auto}  unknown={unknown}")
print()

# Show a few durations
print("Sample durations:")
for rec in records[:5]:
    print(f"  {rec['metadata']['case_name'][:50]:50s}  {rec['metadata']['duration']}")
