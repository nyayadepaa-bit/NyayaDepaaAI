"""
utils/pdf_extractor.py
----------------------
Extracts clean text from all PDFs in data/raw_pdfs/.
Handles both digital PDFs (PyMuPDF) and scanned PDFs (OCR via pytesseract).
Output: data/processed/corpus.jsonl  — one JSON object per document chunk.
"""

import os
import json
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

import fitz  # PyMuPDF
import pdfplumber

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG — adjust if needed
# ============================================================
RAW_PDF_DIR = Path("../data/raw_pdfs")
OUTPUT_DIR  = Path("../data/processed")
OUTPUT_FILE = OUTPUT_DIR / "corpus.jsonl"
MIN_TEXT_LENGTH = 100   # Minimum chars per page to be considered valid
OCR_FALLBACK   = True   # Use OCR if extracted text is too short
# ============================================================


def extract_with_pymupdf(pdf_path: Path) -> list[dict]:
    """Extract text page-by-page using PyMuPDF (fast, digital PDFs)."""
    pages = []
    with fitz.open(str(pdf_path)) as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text("text").strip()
            if len(text) >= MIN_TEXT_LENGTH:
                pages.append({
                    "source": pdf_path.name,
                    "page": page_num + 1,
                    "text": text,
                    "method": "pymupdf"
                })
    return pages


def extract_with_pdfplumber(pdf_path: Path) -> list[dict]:
    """Extract text using pdfplumber (better for tables)."""
    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            text = text.strip()
            if len(text) >= MIN_TEXT_LENGTH:
                pages.append({
                    "source": pdf_path.name,
                    "page": page_num + 1,
                    "text": text,
                    "method": "pdfplumber"
                })
    return pages


def extract_with_ocr(pdf_path: Path) -> list[dict]:
    """OCR fallback for scanned PDFs using pytesseract."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("pytesseract/Pillow not installed. Skipping OCR.")
        return []

    pages = []
    with fitz.open(str(pdf_path)) as doc:
        for page_num, page in enumerate(doc):
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang="eng").strip()
            if len(text) >= MIN_TEXT_LENGTH:
                pages.append({
                    "source": pdf_path.name,
                    "page": page_num + 1,
                    "text": text,
                    "method": "ocr"
                })
    return pages


def process_pdf(pdf_path: Path) -> list[dict]:
    """Try extraction methods in order of preference."""
    logger.info(f"Processing: {pdf_path.name}")

    pages = extract_with_pymupdf(pdf_path)
    if pages:
        return pages

    logger.info(f"  PyMuPDF returned little text, trying pdfplumber...")
    pages = extract_with_pdfplumber(pdf_path)
    if pages:
        return pages

    if OCR_FALLBACK:
        logger.info(f"  Falling back to OCR for {pdf_path.name}")
        pages = extract_with_ocr(pdf_path)

    return pages


def main():
    parser = argparse.ArgumentParser(description="Extract text from legal PDFs")
    parser.add_argument("--input_dir", type=str, default=str(RAW_PDF_DIR))
    parser.add_argument("--output_file", type=str, default=str(OUTPUT_FILE))
    args = parser.parse_args()

    input_dir  = Path(args.input_dir)
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDFs found in {input_dir}. Place your PDFs there and re-run.")
        return

    logger.info(f"Found {len(pdf_files)} PDFs in {input_dir}")
    total_pages = 0

    with open(output_file, "w", encoding="utf-8") as f:
        for pdf_path in tqdm(pdf_files, desc="Extracting PDFs"):
            pages = process_pdf(pdf_path)
            for page in pages:
                f.write(json.dumps(page, ensure_ascii=False) + "\n")
            total_pages += len(pages)

    logger.info(f"Done! Extracted {total_pages} pages → {output_file}")


if __name__ == "__main__":
    main()
