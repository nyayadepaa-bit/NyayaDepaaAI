"""
data/enrich_judge_reasoning.py
-------------------------------
Enriches legal_cases.json and legal_cases_pinecone.jsonl with a
`judge_reasoning` field synthesized from existing metadata:
  - court_observations (judge's notes)
  - final_order (actual order text)
  - judgement_summary (case summary)
  - case_result + case_laws + allegations (for context)

Also adds a `decision_basis` field that categorizes WHY the judge decided.

Run:  python data/enrich_judge_reasoning.py
"""

import json
import re
import os

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEGAL_CASES_JSON = os.path.join(BASE_DIR, "legal_cases.json")
LEGAL_CASES_JSONL = os.path.join(BASE_DIR, "legal_cases_pinecone.jsonl")


# ── Decision basis categories ──
# These capture WHY a judge decided a certain way
DECISION_BASIS_PATTERNS = {
    "Insufficient Evidence": [
        r"insufficien\w+ evidence",
        r"lack of (proof|evidence|corroboration)",
        r"no (cogent|reliable|sufficient) evidence",
        r"failed to (prove|establish|substantiate)",
        r"prosecution .*(failed|unable)",
        r"absence of (evidence|proof|witness)",
        r"not (proved|proven|established)",
    ],
    "Strong Documentary Evidence": [
        r"medical (report|evidence|certificate)",
        r"documentary (proof|evidence)",
        r"FIR.+(corroborate|support|establish)",
        r"proved (by|through|with) (documents|records|evidence)",
        r"medical.+injuries.+(confirm|establish|corroborate)",
    ],
    "Witness Testimony": [
        r"(credible|reliable) witness",
        r"testimony.+(establish|prove|confirm|corroborate)",
        r"deposed.+(confirm|establish)",
        r"witness.+(support|corroborate)",
        r"eye.?witness",
    ],
    "Statutory Protection": [
        r"(section|sec\.?) (498A|354|376|304B|125|12)",
        r"PWDVA|Protection of Women|Domestic Violence Act",
        r"POSH Act|Sexual Harassment.*Workplace",
        r"Hindu (Marriage|Succession|Adoption) Act",
        r"Dowry Prohibition Act",
        r"CrPC|Cr\.P\.C|BNSS",
        r"statutory (right|entitlement|protection|obligation)",
    ],
    "Cruelty Established": [
        r"cruelty.+(proved|established|found)",
        r"(mental|physical) (torture|cruelty|harassment)",
        r"(matrimonial|domestic) cruelty",
        r"demanded dowry",
        r"subjected.*cruelty",
    ],
    "Financial Need / Dependency": [
        r"(unable|incapable).+maintain (herself|themselves)",
        r"(financially|economically) (dependent|weak|helpless)",
        r"no (independent|separate) (source|means).+income",
        r"(entitled|deserves).+maintenance",
        r"maintain.*standard of living",
        r"earning capacity.+(husband|respondent)",
    ],
    "Procedural Grounds": [
        r"(limitation|jurisdiction|locus|maintainability)",
        r"not.+jurisdiction",
        r"procedural (defect|irregularity|lapse)",
        r"time.?barred",
        r"filing.+(delay|late)",
    ],
    "Settlement / Compromise": [
        r"(mutual|amicable) (settlement|consent|compromise)",
        r"parties.+(agree|settle|compromise)",
        r"mediation",
        r"conciliation",
    ],
    "Child Welfare / Best Interest": [
        r"(best interest|welfare).+(child|minor)",
        r"custody.+(child|minor)",
        r"(child|minor).+(safety|welfare|protection)",
    ],
    "Habitual Offender / Repeat Conduct": [
        r"(habitual|repeat|persistent).+(offend|conduct|behavior|behaviour)",
        r"(previous|prior) (complaint|incident|FIR|case)",
        r"pattern of (abuse|violence|harassment)",
    ],
}


def _classify_decision_basis(text: str) -> list[str]:
    """
    Classify the decision basis from combined text (observations + order + summary).
    Returns a list of basis categories.
    """
    bases = []
    lower = text.lower()
    for category, patterns in DECISION_BASIS_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lower, re.IGNORECASE):
                bases.append(category)
                break  # One match per category is enough
    return bases if bases else ["General Judicial Discretion"]


def _build_judge_reasoning(meta: dict) -> str:
    """
    Synthesize a judge_reasoning string from available metadata fields.
    """
    parts = []

    result = meta.get("case_result", "Unknown")
    laws = meta.get("case_laws", [])
    allegations = meta.get("allegations", [])
    observations = meta.get("court_observations", "")
    final_order = meta.get("final_order", "")
    summary = meta.get("judgement_summary", "")
    court = meta.get("court", "")
    legal_area = meta.get("legal_area", "")
    evidence = meta.get("evidence_types", [])

    # Start with the decision
    parts.append(f"The court ruled: {result}.")

    # Court observations — most valuable for reasoning
    if observations and observations not in ("Not extracted", "Unknown", ""):
        # Clean encoding artifacts
        clean_obs = observations.replace("\u201c", '"').replace("\u201d", '"')
        clean_obs = re.sub(r'â€[œ"]', '"', clean_obs)
        parts.append(f"Court observed: {clean_obs}")

    # Final order — captures the directive
    if final_order and final_order not in ("Not extracted", "Unknown", ""):
        clean_order = final_order[:500]  # Truncate very long orders
        parts.append(f"Final order: {clean_order}")

    # Summary — always available
    if summary and summary not in ("Not extracted", "Unknown", ""):
        parts.append(f"Case context: {summary}")

    # Laws applied
    if laws and laws != ["Unknown"]:
        parts.append(f"Laws applied: {', '.join(laws)}.")

    # Evidence considered
    if evidence and evidence != ["Unknown"]:
        parts.append(f"Evidence considered: {', '.join(evidence)}.")

    return " ".join(parts)


def _update_text_field(text: str, judge_reasoning: str, decision_basis: list[str]) -> str:
    """
    Append judge reasoning and decision basis to the text field
    so it's searchable in vector embeddings.
    """
    additions = []
    additions.append(f"Judge Reasoning: {judge_reasoning}")
    additions.append(f"Decision Basis : {', '.join(decision_basis)}")
    return text + "\n" + "\n".join(additions)


def enrich_legal_cases_json():
    """Enrich legal_cases.json with judge_reasoning and decision_basis."""
    print(f"Reading {LEGAL_CASES_JSON}...")
    with open(LEGAL_CASES_JSON, "r", encoding="utf-8") as f:
        cases = json.load(f)

    enriched = 0
    for case in cases:
        meta = case.get("metadata", {})

        # Build judge reasoning
        reasoning = _build_judge_reasoning(meta)
        meta["judge_reasoning"] = reasoning

        # Classify decision basis
        combined_text = " ".join([
            meta.get("court_observations", ""),
            meta.get("final_order", ""),
            meta.get("judgement_summary", ""),
            str(meta.get("case_laws", "")),
            str(meta.get("allegations", "")),
        ])
        basis = _classify_decision_basis(combined_text)
        meta["decision_basis"] = basis

        # Update the text field for better embedding search
        case["text"] = _update_text_field(case.get("text", ""), reasoning, basis)
        case["metadata"] = meta
        enriched += 1

    # Write back
    with open(LEGAL_CASES_JSON, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"✓ Enriched {enriched} cases in legal_cases.json")
    return cases


def enrich_legal_cases_jsonl(cases_from_json: list):
    """
    Enrich legal_cases_pinecone.jsonl using the same enrichment data.
    Handles both single-line JSONL and multi-line (pretty-printed) JSONL.
    """
    print(f"Reading {LEGAL_CASES_JSONL}...")

    # Build lookup from enriched JSON
    lookup = {}
    for case in cases_from_json:
        lookup[case["id"]] = case

    # Read entire file and parse JSON objects
    with open(LEGAL_CASES_JSONL, "r", encoding="utf-8") as f:
        content = f.read()

    # Try to parse as a stream of JSON objects
    records = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(content):
        # Skip whitespace
        while idx < len(content) and content[idx] in ' \t\n\r':
            idx += 1
        if idx >= len(content):
            break
        try:
            obj, end_idx = decoder.raw_decode(content, idx)
            records.append(obj)
            idx = end_idx
        except json.JSONDecodeError:
            idx += 1

    print(f"  Parsed {len(records)} JSON records")

    enriched = 0
    for record in records:
        rid = record.get("id", "")
        if rid in lookup:
            enriched_case = lookup[rid]
            record["text"] = enriched_case["text"]
            record["metadata"] = enriched_case["metadata"]
            enriched += 1

    # Write back as one JSON object per line (proper JSONL)
    with open(LEGAL_CASES_JSONL, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"✓ Enriched {enriched} records in legal_cases_pinecone.jsonl")


def show_samples(cases: list, n: int = 5):
    """Print sample enrichment results."""
    count = 0
    for case in cases:
        meta = case["metadata"]
        if count >= n:
            break
        print(f"\n{'='*70}")
        print(f"Case Result   : {meta['case_result']}")
        print(f"Legal Area    : {meta['legal_area']}")
        print(f"Decision Basis: {meta['decision_basis']}")
        print(f"Judge Reasoning (first 300 chars):")
        print(f"  {meta['judge_reasoning'][:300]}")
        count += 1


if __name__ == "__main__":
    cases = enrich_legal_cases_json()
    enrich_legal_cases_jsonl(cases)
    print("\n" + "="*70)
    print("SAMPLE ENRICHMENTS:")
    show_samples(cases)
    print(f"\n✓ Done! Both files enriched with judge_reasoning + decision_basis.")
