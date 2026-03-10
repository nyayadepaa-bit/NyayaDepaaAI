"""
pipeline/dataset_builder.py
----------------------------
Extracts text from all PDFs in /pdfs, cleans it, detects legal structure,
classifies into legal categories, and outputs data/dataset.jsonl.

Output format per record:
    {
        "source": "filename.pdf",
        "page": 1,
        "text": "cleaned page text",
        "act_name": "Protection of Women from Domestic Violence Act, 2005",
        "legal_category": "domestic_violence",
        "sections_found": ["Section 3", "Section 12"],
        "method": "pymupdf"
    }
"""

import re
import json
import logging
from pathlib import Path
from typing import Optional

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24
except ImportError:
    try:
        import fitz  # PyMuPDF older versions
    except ImportError:
        fitz = None
import pdfplumber

logger = logging.getLogger(__name__)

# ── Legal Category Classification ─────────────────────────
CATEGORY_PATTERNS = {
    "domestic_violence": [
        r"domestic\s*violence", r"protection\s*of\s*women", r"DV\s*Act",
        r"matrimonial\s*cruelty", r"dowry", r"498[\s\-]?A", r"streedhan",
        r"maintenance", r"shared\s*household", r"protection\s*order",
    ],
    "workplace_harassment": [
        r"sexual\s*harassment.*workplace", r"POSH", r"vishakha",
        r"internal\s*complaints?\s*committee", r"ICC",
        r"workplace\s*safety", r"employer.*liability",
    ],
    "cyber_crime": [
        r"cyber\s*(crime|harassment|stalking|bullying)",
        r"information\s*technology\s*act", r"IT\s*Act",
        r"section\s*66[A-F]?", r"section\s*67",
        r"online\s*(harassment|abuse|threat)", r"revenge\s*porn",
        r"morphing", r"obscene.*electronic",
    ],
    "criminal_law": [
        r"indian\s*penal\s*code", r"IPC", r"BNS", r"bharatiya\s*nyaya",
        r"section\s*3[0-9]{2}", r"section\s*37[0-9]",
        r"rape", r"molestation", r"assault", r"kidnapping",
        r"outrag.*modesty", r"voyeurism", r"stalking",
        r"acid\s*attack", r"crpc", r"BNSS",
    ],
    "reporting_procedure": [
        r"FIR", r"first\s*information\s*report", r"police\s*complaint",
        r"zero\s*FIR", r"e[\s\-]?FIR", r"how\s*to\s*(file|register|lodge)",
        r"women\s*(helpline|commission|cell)",
        r"legal\s*aid", r"magistrate.*complaint", r"NCW",
    ],
    "case_duration": [
        r"time\s*(limit|frame|period)", r"limitation\s*period",
        r"disposal.*case", r"pendency", r"adjournment",
        r"fast\s*track\s*court", r"trial.*duration",
    ],
}

# ── Act Name Detection ────────────────────────────────────
ACT_PATTERNS = [
    (r"Protection\s+of\s+Women\s+from\s+Domestic\s+Violence\s+Act[,\s]*\d*", "Protection of Women from Domestic Violence Act, 2005"),
    (r"Sexual\s+Harassment\s+of\s+Women.*Workplace.*Act[,\s]*\d*", "Sexual Harassment at Workplace Act, 2013"),
    (r"Indian\s+Penal\s+Code[,\s]*\d*", "Indian Penal Code, 1860"),
    (r"Bharatiya\s+Nyaya\s+Sanhita[,\s]*\d*", "Bharatiya Nyaya Sanhita, 2023"),
    (r"Code\s+of\s+Criminal\s+Procedure[,\s]*\d*", "Code of Criminal Procedure, 1973"),
    (r"Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita[,\s]*\d*", "Bharatiya Nagarik Suraksha Sanhita, 2023"),
    (r"Information\s+Technology\s+Act[,\s]*\d*", "Information Technology Act, 2000"),
    (r"Dowry\s+Prohibition\s+Act[,\s]*\d*", "Dowry Prohibition Act, 1961"),
    (r"Hindu\s+Marriage\s+Act[,\s]*\d*", "Hindu Marriage Act, 1955"),
    (r"Muslim\s+Women.*Protection.*Rights.*Act[,\s]*\d*", "Muslim Women (Protection of Rights) Act"),
    (r"Indecent\s+Representation\s+of\s+Women.*Act[,\s]*\d*", "Indecent Representation of Women Act, 1986"),
    (r"Maternity\s+Benefit\s+Act[,\s]*\d*", "Maternity Benefit Act, 1961"),
    (r"Equal\s+Remuneration\s+Act[,\s]*\d*", "Equal Remuneration Act, 1976"),
    (r"POCSO\s+Act|Protection\s+of\s+Children\s+from\s+Sexual\s+Offences", "POCSO Act, 2012"),
    (r"National\s+Commission\s+for\s+Women\s+Act", "National Commission for Women Act, 1990"),
]

SECTION_PATTERN = re.compile(
    r"(?:Section|Sec\.|S\.)\s*(\d+[A-Za-z]*(?:\s*\(\d+\))?)", re.IGNORECASE
)


def clean_text(text: str) -> str:
    """Remove noise while preserving legal structure."""
    # Remove page numbers
    text = re.sub(r"(?m)^\s*[-–—]?\s*\d+\s*[-–—]?\s*$", "", text)
    text = re.sub(r"(?m)^Page\s*\d+\s*(?:of\s*\d+)?\s*$", "", text, flags=re.IGNORECASE)
    # Remove common headers/footers
    text = re.sub(r"(?m)^.*(?:All\s*Rights\s*Reserved|©|www\.|http).*$", "", text, flags=re.IGNORECASE)
    # Collapse excessive whitespace but keep paragraph structure
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{3,}", " ", text)
    return text.strip()


def detect_act_name(text: str) -> Optional[str]:
    """Detect which legal act the text is about."""
    for pattern, name in ACT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return None


def detect_sections(text: str) -> list[str]:
    """Extract section references from text."""
    matches = SECTION_PATTERN.findall(text)
    return [f"Section {m}" for m in matches[:10]]  # cap at 10


def classify_category(text: str) -> str:
    """Classify text into a legal category based on keyword patterns."""
    scores = {}
    text_lower = text.lower()
    for category, patterns in CATEGORY_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, text_lower))
        if score > 0:
            scores[category] = score

    if scores:
        return max(scores, key=scores.get)
    return "general"


def extract_pdf_pymupdf(pdf_path: Path) -> list[dict]:
    """Extract text page-by-page using PyMuPDF."""
    pages = []
    try:
        with fitz.open(str(pdf_path)) as doc:
            for page_num, page in enumerate(doc):
                text = page.get_text("text").strip()
                if len(text) >= 80:
                    pages.append({
                        "source": pdf_path.name,
                        "page": page_num + 1,
                        "text": text,
                        "method": "pymupdf",
                    })
    except Exception as e:
        logger.warning(f"PyMuPDF failed for {pdf_path.name}: {e}")
    return pages


def extract_pdf_pdfplumber(pdf_path: Path) -> list[dict]:
    """Fallback extraction using pdfplumber."""
    pages = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").strip()
                if len(text) >= 80:
                    pages.append({
                        "source": pdf_path.name,
                        "page": page_num + 1,
                        "text": text,
                        "method": "pdfplumber",
                    })
    except Exception as e:
        logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}")
    return pages


def process_pdf(pdf_path: Path) -> list[dict]:
    """Extract, clean, and enrich a single PDF."""
    pages = extract_pdf_pymupdf(pdf_path)
    if not pages:
        pages = extract_pdf_pdfplumber(pdf_path)

    enriched = []
    for page in pages:
        cleaned = clean_text(page["text"])
        if len(cleaned) < 80:
            continue

        enriched.append({
            "source": page["source"],
            "page": page["page"],
            "text": cleaned,
            "act_name": detect_act_name(cleaned),
            "sections_found": detect_sections(cleaned),
            "legal_category": classify_category(cleaned),
            "method": page["method"],
        })

    return enriched


def build_dataset(pdf_dir: Path, output_file: Path) -> int:
    """
    Process all PDFs and write dataset.jsonl.

    Returns:
        Number of records written.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error(f"No PDFs found in {pdf_dir}")
        return 0

    logger.info(f"Processing {len(pdf_files)} PDFs from {pdf_dir}")
    total = 0

    with open(output_file, "w", encoding="utf-8") as f:
        for pdf_path in pdf_files:
            records = process_pdf(pdf_path)
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total += len(records)

            if total % 200 == 0 and total > 0:
                logger.info(f"  ...{total} records so far")

    logger.info(f"Dataset complete: {total} records → {output_file}")
    return total
