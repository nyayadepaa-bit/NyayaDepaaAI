"""
pipeline/chunker.py
--------------------
Legal-aware semantic chunking.

Splits text by legal boundaries (sections, clauses, paragraphs)
instead of fixed character count. Attaches rich metadata per chunk.
"""

import re
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Legal Boundary Patterns ───────────────────────────────
# These mark natural split points in legal text
LEGAL_SEPARATORS = [
    r"\n(?=(?:Section|SECTION|Sec\.)\s*\d+)",       # Section boundary
    r"\n(?=(?:Article|ARTICLE)\s*\d+)",              # Article boundary
    r"\n(?=\d+\.\s+[A-Z])",                          # Numbered clause
    r"\n(?=\([a-z]\)\s)",                             # Sub-clause (a), (b)
    r"\n(?=(?:Chapter|CHAPTER)\s+[IVXLCDM]+)",       # Chapter boundary
    r"\n(?=(?:Schedule|SCHEDULE)\s)",                 # Schedule boundary
    r"\n\n",                                          # Paragraph boundary
    r"\n",                                            # Line boundary (last resort)
]

KEYWORD_PATTERNS = [
    (r"(?:sexual\s*harassment|POSH|vishakha|ICC)", "sexual_harassment"),
    (r"(?:domestic\s*violence|DV\s*Act|protection\s*order)", "domestic_violence"),
    (r"(?:dowry|498[\s-]?A|streedhan|cruelty.*husband)", "dowry"),
    (r"(?:rape|section\s*37[56]|penetrative|consent)", "sexual_assault"),
    (r"(?:stalking|voyeurism|outrag.*modesty)", "stalking_voyeurism"),
    (r"(?:cyber|online.*harass|IT\s*Act|morphing|revenge\s*porn)", "cyber_crime"),
    (r"(?:FIR|police\s*complaint|zero\s*FIR|e-?FIR)", "fir_procedure"),
    (r"(?:maintenance|alimony|custody|divorce)", "family_law"),
    (r"(?:bail|anticipatory|arrest)", "bail_arrest"),
    (r"(?:compensation|damages|relief)", "compensation"),
    (r"(?:acid\s*attack|trafficking|forced\s*labour)", "serious_crime"),
    (r"(?:helpline|women\s*commission|NCW|legal\s*aid)", "helpline_resources"),
    (r"(?:maternity|equal\s*remuneration|workplace)", "employment"),
]


def extract_keywords(text: str) -> list[str]:
    """Extract legal topic keywords from text."""
    keywords = []
    text_lower = text.lower()
    for pattern, keyword in KEYWORD_PATTERNS:
        if re.search(pattern, text_lower):
            keywords.append(keyword)
    return keywords


def _make_chunk_id(source: str, page: int, index: int) -> str:
    """Generate a deterministic chunk ID for dedup."""
    raw = f"{source}::{page}::{index}"
    return hashlib.md5(raw.encode()).hexdigest()


def semantic_split(text: str, max_size: int = 800, min_size: int = 100) -> list[str]:
    """
    Split text by legal boundaries, preferring natural split points.
    Falls back to progressively finer boundaries if chunks are too large.
    """
    # Try each separator level, from coarsest to finest
    for sep_pattern in LEGAL_SEPARATORS:
        segments = re.split(sep_pattern, text)
        segments = [s.strip() for s in segments if s.strip()]

        # Check if all segments are within size limit
        if all(len(s) <= max_size * 1.3 for s in segments):
            # Merge small segments
            merged = _merge_small(segments, max_size, min_size)
            if merged:
                return merged

    # Fallback: fixed-size split
    return _fixed_split(text, max_size, max_size // 5)


def _merge_small(segments: list[str], max_size: int, min_size: int) -> list[str]:
    """Merge segments that are too small."""
    merged = []
    current = ""

    for seg in segments:
        if len(current) + len(seg) + 1 <= max_size:
            current = (current + "\n" + seg).strip() if current else seg
        else:
            if len(current) >= min_size:
                merged.append(current)
            elif merged:
                merged[-1] = merged[-1] + "\n" + current
            current = seg

    if current:
        if len(current) >= min_size:
            merged.append(current)
        elif merged:
            merged[-1] = merged[-1] + "\n" + current

    return merged


def _fixed_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Fixed-size split with overlap (fallback)."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
        if start <= 0 and end >= len(text):
            break
    return chunks


def chunk_record(record: dict, chunk_size: int = 800, overlap: int = 150) -> list[dict]:
    """
    Chunk a single dataset record into semantically meaningful pieces.

    Args:
        record: dict from dataset.jsonl with text, source, page, etc.
        chunk_size: target max characters per chunk
        overlap: overlap between fixed-split chunks (fallback only)

    Returns:
        List of chunk dicts with full metadata.
    """
    text = record["text"]
    if len(text) < 100:
        return []

    segments = semantic_split(text, max_size=chunk_size, min_size=100)
    chunks = []

    for i, seg_text in enumerate(segments):
        chunk_id = _make_chunk_id(record["source"], record["page"], i)
        keywords = extract_keywords(seg_text)

        chunks.append({
            "id": chunk_id,
            "text": seg_text,
            "metadata": {
                "source": record["source"],
                "page": record["page"],
                "chunk_index": i,
                "total_chunks": len(segments),
                "act_name": record.get("act_name", ""),
                "legal_category": record.get("legal_category", "general"),
                "sections_found": ", ".join(record.get("sections_found", [])),
                "keywords": ", ".join(keywords),
                "char_count": len(seg_text),
            },
        })

    return chunks


def chunk_dataset(records: list[dict], chunk_size: int = 800, overlap: int = 150) -> list[dict]:
    """Chunk all records from dataset.jsonl."""
    all_chunks = []
    for rec in records:
        all_chunks.extend(chunk_record(rec, chunk_size, overlap))

    logger.info(f"Chunked {len(records)} records → {len(all_chunks)} chunks")
    return all_chunks
