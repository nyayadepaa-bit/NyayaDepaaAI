"""
data/extract_pdf_cases.py
--------------------------
Deep extraction of all legal variables from PDF case files.
Computes duration automatically from filing/decision dates if not explicit.
Extracts 30+ fields to enable judge-level reasoning in the RAG bot.

Run:
  python data/extract_pdf_cases.py
"""

import json
import logging
import re
import pdfplumber
from datetime import datetime, date
from pathlib import Path
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PDF_DIR         = Path("d:/LegalLlama3/pdfs")
PINECONE_OUTPUT = Path("d:/LegalLlama3/data/legal_cases_pinecone.jsonl")
JSON_OUTPUT     = Path("d:/LegalLlama3/data/legal_cases.json")


# ─────────────────── Helpers ────────────────────────────────────

def safe_id(name: str, idx: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\-]", "-", name)[:40]
    return f"{slug}-{idx:04d}"


def extract_full_text(pdf_path: Path) -> str:
    """Extract all text from all pages of a PDF."""
    txt = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    txt.append(t)
    except Exception as e:
        logger.error(f"Error reading {pdf_path.name}: {e}")
    return "\n".join(txt).strip()


def _c(s: str, maxlen: int = 100) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", s).strip()[:maxlen]


# ─────────────────── Date Utilities ─────────────────────────────

DATE_PATTERNS = [
    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})",
    # D Month YYYY or DDth Month YYYY
    r"(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{4})",
    # Month D, YYYY
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})",
]

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _parse_date(text: str) -> date | None:
    """Try to parse a date string into a date object."""
    # Numeric DD/MM/YYYY
    m = re.match(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", text.strip())
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    # "15 March 2022" or "15th March 2022"
    m = re.match(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+"
        r"(January|February|March|April|May|June|July|August|September"
        r"|October|November|December)\s+(\d{4})",
        text.strip(), re.IGNORECASE,
    )
    if m:
        try:
            return date(int(m.group(3)), MONTH_MAP[m.group(2).lower()], int(m.group(1)))
        except (ValueError, KeyError):
            pass

    # "March 15, 2022"
    m = re.match(
        r"(January|February|March|April|May|June|July|August|September"
        r"|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})",
        text.strip(), re.IGNORECASE,
    )
    if m:
        try:
            return date(int(m.group(3)), MONTH_MAP[m.group(1).lower()], int(m.group(2)))
        except (ValueError, KeyError):
            pass

    return None


def _find_date(text: str, patterns: list[str]) -> tuple[str, date | None]:
    """
    Search for a date using context patterns.
    Returns (raw_string, date_object).
    """
    date_re = (
        r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}"
        r"|\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July"
        r"|August|September|October|November|December)\s+\d{4}"
        r"|(?:January|February|March|April|May|June|July|August|September"
        r"|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})"
    )
    for ctx in patterns:
        m = re.search(ctx + r"[\s:–\-]*" + date_re, text, re.IGNORECASE)
        if m:
            raw = m.group(1)
            return raw, _parse_date(raw)
    return "Unknown", None


def _compute_duration(d1: date | None, d2: date | None) -> str:
    """Compute human-readable duration between two dates."""
    if d1 is None or d2 is None:
        return "Unknown"
    if d2 < d1:
        d1, d2 = d2, d1
    delta = d2 - d1
    total_months = delta.days // 30
    years  = total_months // 12
    months = total_months % 12
    days   = delta.days % 30
    parts  = []
    if years:
        parts.append(f"{years}Y")
    if months:
        parts.append(f"{months}M")
    if days or not parts:
        parts.append(f"{days}D")
    return " ".join(parts) + f" ({delta.days} days total)"


# ─────────────────── Deep Parser ────────────────────────────────

def parse_case(text: str, filename: str, idx: int) -> dict:
    """
    Deep, word-by-word extraction of every legally relevant variable.
    Produces 30+ fields for judge-level RAG reasoning.
    """
    upper  = text.upper()
    head   = text[:4000]       # top of document — structured header info
    mid    = text[2000:8000]   # body — arguments, evidence
    tail   = text[-4000:]      # judgment section
    tail_l = tail.lower()

    # ══ 1. COURT ═══════════════════════════════════════════════
    court = "District Court"
    if "SUPREME COURT" in upper:
        court = "Supreme Court of India"
    elif "HIGH COURT" in upper:
        hc = re.search(r"HIGH COURT\s+OF\s+([\w\s]+?)(?:\n|,|AT\b)", upper)
        court = f"High Court of {hc.group(1).strip().title()}" if hc else "High Court of India"
    elif "SESSIONS" in upper:
        court = "Sessions Court"
    elif "MAGISTRATE" in upper or "JMFC" in upper or "J.M.F.C" in upper:
        court = "Judicial Magistrate Court"
    elif "FAMILY COURT" in upper:
        court = "Family Court"

    # ══ 2. PARTIES ═════════════════════════════════════════════
    petitioner = "Unknown"
    respondent  = "Unknown"
    case_name   = filename.replace(".pdf", "")

    vs_m = re.search(
        r"([A-Za-z][\w\s\.,]{3,60})\s+(?:V[sS]?\.?\s+|VERSUS\s+|V/S\s+)"
        r"([A-Za-z][\w\s\.,]{3,60})",
        head,
    )
    if vs_m:
        p = _c(vs_m.group(1).split("\n")[-1], 80)
        r = _c(vs_m.group(2).split("\n")[0],  80)
        if len(p) > 3 and len(r) > 3:
            petitioner = p
            respondent  = r
            case_name   = f"{petitioner} vs {respondent}"
    case_name = _c(case_name, 140)

    # ══ 3. ROLE LABELS (who filed, against whom) ═══════════════
    filed_by = "Unknown"
    fb = re.search(
        r"([\w\s\.]{4,80}?)[,\s]*\.{2,}\s*(?:Appellant|Applicant|Petitioner|Complainant)",
        head, re.IGNORECASE,
    )
    if fb:
        filed_by = _c(fb.group(1))

    filed_against = "Unknown"
    fa = re.search(
        r"([\w\s\.]{4,80}?)[,\s]*\.{2,}\s*(?:Respondent|Accused|Opponent|Non-Applicant)",
        head, re.IGNORECASE,
    )
    if fa:
        filed_against = _c(fa.group(1))

    # ══ 4. CASE / APPEAL NUMBER ════════════════════════════════
    appeal_number = "Unknown"
    ap = re.search(
        r"(?:CRIMINAL\s+APPEAL|CRI\.?\s+APPEAL|Cri\.?\s+Appeal|CRIMINAL\s+REVISION"
        r"|CRIMINAL\s+MISC\.?\s*APPLICATION|FIRST\s+APPEAL|MISC\.\s*PETITION"
        r"|WRIT\s+PETITION|CIVIL\s+APPEAL)"
        r"[\s\.]*(?:No\.?|NO\.?)?\s*([\d\/\(\)\s]+(?:of\s*\d{4})?)",
        head, re.IGNORECASE,
    )
    if ap:
        appeal_number = _c(ap.group(1), 60)

    # ══ 5. FIR NUMBER & POLICE STATION ════════════════════════
    fir_number = "Unknown"
    fir_m = re.search(r"FIR\s*(?:No\.?|:)?\s*(\d+[\s\/\-]*(?:of\s*\d{4})?)", text, re.IGNORECASE)
    if fir_m:
        fir_number = _c(fir_m.group(1), 30)

    police_station = "Unknown"
    ps_m = re.search(
        r"(?:Police\s+Station|P\.S\.?)\s*[,:\-]?\s*([\w\s]+?)(?:\n|,|\.)",
        text, re.IGNORECASE,
    )
    if ps_m:
        police_station = _c(ps_m.group(1), 60)

    # ══ 6. JUDGE NAME ══════════════════════════════════════════
    judge_name = "Unknown"
    # Try multiple patterns
    for pat in [
        r"(?:Before|Coram|BEFORE|HON'?BLE)\s*:?\s*(?:MR\.?|MS\.?|MRS\.?|SMT\.?|SHRI\.?|DR\.?|JUSTICE\s+)?"
        r"([\w\s\.\-]{5,60})(?:\n|,|\r)",
        r"(?:Presided\s+over\s+by)\s*[:–]?\s*([\w\s\.]{5,60})(?:\n|,|\))",
    ]:
        jm = re.search(pat, head, re.IGNORECASE)
        if jm:
            judge_name = _c(jm.group(1).strip().rstrip(",.:"))
            break

    # ══ 7. DATES ═══════════════════════════════════════════════
    filing_date_str, filing_date_obj = _find_date(text[:1500], [
        r"(?:Received|Filed|Presented|Instituted|Date\s+of\s+(?:Filing|Institution))\s*",
        r"(?:Complaint|Petition)\s+(?:filed|dated|received)\s+",
    ])
    decision_date_str, decision_date_obj = _find_date(text[-3000:] + text[:1500], [
        r"(?:Decided\s+on|Date\s+of\s+(?:Decision|Order|Judgment)|Pronounced\s+on|Order\s+dated)\s*",
        r"(?:Judgment|Order)\s+(?:passed|delivered|pronounced)\s+(?:on|dated)\s*",
    ])

    # ══ 8. DURATION (auto-compute if needed) ═══════════════════
    duration = "Unknown"
    # Try explicit duration field first
    dur_m = re.search(r"Duration\s*[:\-]?\s*((?:\d+\s*Y[^\n]{0,40}))", text[:1200], re.IGNORECASE)
    if dur_m:
        duration = _c(dur_m.group(1), 50)
    elif filing_date_obj and decision_date_obj:
        duration = _compute_duration(filing_date_obj, decision_date_obj)
        logger.debug(f"  Auto-computed duration: {duration} ({filename})")
    else:
        # Fallback: look for any year-month pattern in the header
        ym = re.search(r"(\d{2}Y\.\d{2}M\.\d{2}D)", text[:600])
        if ym:
            duration = ym.group(1)

    # ══ 9. CNR ═════════════════════════════════════════════════
    cnr = "Unknown"
    cnr_m = re.search(r"CNR\s*(?:No\.?|:)?\s*[:\-]?\s*([\w\/\-]+)", text[:600], re.IGNORECASE)
    if cnr_m:
        cnr = _c(cnr_m.group(1), 30)

    # ══ 10. YEAR ═══════════════════════════════════════════════
    year = (
        decision_date_obj.year if decision_date_obj
        else (filing_date_obj.year if filing_date_obj else 2023)
    )
    if year == 2023:  # fallback regex
        y_m = re.search(r"\b(20\d{2}|19\d{2})\b", text[:1500])
        if y_m:
            year = int(y_m.group(1))

    # ══ 11. ALLEGATIONS / OFFENCES ════════════════════════════
    allegations = []
    if re.search(r"498\s*[Aa]", text):
        allegations.append("Cruelty by husband/relatives (Section 498A IPC)")
    if re.search(r"DOMESTIC\s+VIOLENCE|PWDVA|D\.V\.\s+ACT|DV\s+ACT", upper):
        allegations.append("Domestic Violence (PWDVA 2005)")
    if re.search(r"DOWRY|DOWRY\s+DEATH|304\s*[Bb]", upper):
        allegations.append("Dowry/Dowry Death")
    if re.search(r"125\s*CR\.?P\.?C|125\s*CRPC|125\s*BNSS", upper):
        allegations.append("Maintenance demand (Sec 125 CrPC/BNSS)")
    if re.search(r"SECTION\s*307", upper):
        allegations.append("Attempt to Murder (Section 307 IPC)")
    if re.search(r"SECTION\s*354", upper):
        allegations.append("Outraging Modesty (Section 354 IPC)")
    if re.search(r"SECTION\s*376", upper):
        allegations.append("Rape (Section 376 IPC)")
    if re.search(r"SECTION\s*406", upper):
        allegations.append("Criminal Breach of Trust (Section 406 IPC)")
    if re.search(r"STALKING|SECTION\s*354[dD]", upper):
        allegations.append("Stalking (Section 354D IPC)")
    if re.search(r"SEXUAL\s+HARASSMENT|WORKPLACE\s+HARASS|POSH", upper):
        allegations.append("Sexual Harassment at Workplace (POSH Act 2013)")
    if re.search(r"CYBER|IT\s+ACT|SECTION\s*66[A-Z]|SECTION\s*67", upper):
        allegations.append("Cyber Crime (IT Act)")
    if not allegations:
        allegations = ["Domestic Violence / Women's Rights"]

    # ══ 12. CASE LAWS / SECTIONS CITED ════════════════════════
    cited_sections = []
    sec_m = re.findall(
        r"(?:Section|Sec\.?|S\.)\s*(\d+[A-Za-z]?)\s*(?:of\s+the\s+)?"
        r"(IPC|CrPC|CRPC|BNSS|BNS|PWDVA|CPC|IT Act|Evidence Act|[A-Z][a-z]+\s+Act)?",
        text,
    )
    seen_secs = set()
    for s, act in sec_m:
        label = f"Section {s}" + (f" {act}" if act else "")
        if label not in seen_secs:
            seen_secs.add(label)
            cited_sections.append(label)
    if not cited_sections:
        cited_sections = ["Protection of Women from Domestic Violence Act 2005"]

    # ══ 13. MAINTENANCE AMOUNT ═════════════════════════════════
    maintenance_rs = 0
    maint_m = re.search(
        r"Rs\.?\s*([\d,]+)\s*(?:per\s*month|p\.m\.|\/\-\s*per\s*month|per\s*mensem)",
        text, re.IGNORECASE,
    )
    if maint_m:
        maintenance_rs = int(maint_m.group(1).replace(",", ""))

    # ══ 14. INTERIM RELIEF GRANTED ════════════════════════════
    interim_relief = "None"
    if re.search(r"interim\s+maintenance\s+(?:of|@|Rs)", tail, re.IGNORECASE):
        im = re.search(r"interim\s+maintenance\s+(?:of|@|Rs\.?\s*)([\d,]+)", tail, re.IGNORECASE)
        interim_relief = f"Interim maintenance Rs.{im.group(1)}/month" if im else "Granted"
    elif re.search(r"interim\s+relief\s+(?:is\s+)?(?:granted|allowed)", tail, re.IGNORECASE):
        interim_relief = "Granted"
    elif re.search(r"protection\s+order|residence\s+order", tail, re.IGNORECASE):
        interim_relief = "Protection/Residence Order"

    # ══ 15. BAIL STATUS ════════════════════════════════════════
    bail_status = "Not Applicable"
    if re.search(r"bail\s+(?:is\s+)?granted", tail_l):
        bail_status = "Bail Granted"
    elif re.search(r"bail\s+(?:is\s+)?rejected|bail\s+denied|anticipatory\s+bail.*rejected", tail_l):
        bail_status = "Bail Rejected"
    elif re.search(r"anticipatory\s+bail\s+(?:is\s+)?granted", tail_l):
        bail_status = "Anticipatory Bail Granted"

    # ══ 16. WITNESSES ══════════════════════════════════════════
    witness_count = 0
    wits = re.findall(
        r"\b(?:PW|DW|CW|AW|OW)\s*-?\s*(\d+)\b",          # PW-1, DW-2 etc.
        text,
    )
    if wits:
        witness_count = max(int(w) for w in wits)
    else:
        # Count "witness" mentions
        wc = len(re.findall(r"\bwitness(?:es)?\b", text, re.IGNORECASE))
        witness_count = min(wc, 20)

    # ══ 17. EVIDENCE TYPES MENTIONED ══════════════════════════
    evidence_types = []
    evidence_map   = {
        "Medical certificate": r"medical\s+(?:certificate|report|record)",
        "Photographs": r"photograph|photo\s+evidence",
        "CCTV footage":        r"cctv|cctv\s+footage|video\s+footage",
        "Call records": r"call\s+record|CDR|mobile\s+record",
        "WhatsApp/messages":   r"whatsapp|text\s+message|chat|sms",
        "Bank records": r"bank\s+record|bank\s+statement|account\s+statement",
        "Medical examination": r"medical\s+examination|injury\s+report|MLR",
        "FIR copy": r"F\.I\.R\.|first\s+information\s+report",
        "Affidavit": r"affidavit",
        "Documentary proof": r"documentary\s+evidence|document(?:s)?\s+produced",
    }
    for label, pat in evidence_map.items():
        if re.search(pat, text, re.IGNORECASE):
            evidence_types.append(label)
    if not evidence_types:
        evidence_types = ["Not specified"]

    # ══ 18. PETITIONER ARGUMENTS (key claims) ═════════════════
    petitioner_claims = "Not extracted"
    pet_sec = re.search(
        r"(?:Petitioner|Appellant|Applicant)\s+(?:submits?|contends?|argues?|states?)\s*[:\-]?"
        r"\s*(.{50,400}?)(?:\.\s+[A-Z]|\n\n|\Z)",
        text, re.DOTALL,
    )
    if pet_sec:
        petitioner_claims = _c(pet_sec.group(1), 400)

    # ══ 19. RESPONDENT ARGUMENTS ══════════════════════════════
    respondent_claims = "Not extracted"
    res_sec = re.search(
        r"(?:Respondent|Accused|Opponent)\s+(?:submits?|contends?|argues?|denies?|states?)\s*[:\-]?"
        r"\s*(.{50,400}?)(?:\.\s+[A-Z]|\n\n|\Z)",
        text, re.DOTALL,
    )
    if res_sec:
        respondent_claims = _c(res_sec.group(1), 400)

    # ══ 20. COURT OBSERVATIONS / KEY FINDINGS ═════════════════
    court_observations = "Not extracted"
    obs_sec = re.search(
        r"(?:Court\s+(?:observes?|notes?|finds?|holds?)|We\s+(?:observe|note|find|hold)"
        r"|It\s+is\s+(?:observed|noted|held))\s*[:\-]?\s*"
        r"(.{80,600}?)(?:\.\s+[A-Z]|\n\n|\Z)",
        tail, re.DOTALL | re.IGNORECASE,
    )
    if obs_sec:
        court_observations = _c(obs_sec.group(1), 500)

    # ══ 21. FINAL ORDER ════════════════════════════════════════
    final_order = "Not extracted"
    order_sec = re.search(
        r"(?:ORDER|JUDGMENT|OPERATIVE\s+PART|IN\s+THE\s+RESULT|RESULT|ACCORDINGLY)"
        r"\s*:?\s*\n(.{80,600}?)(?:\n\n|\Z)",
        tail, re.DOTALL | re.IGNORECASE,
    )
    if order_sec:
        final_order = _c(order_sec.group(1), 500)

    # ══ 22. CASE RESULT ════════════════════════════════════════
    case_result = "Petition Dismissed"
    if re.search(r"petition\s+allowed|appeal\s+allowed|application\s+allowed", tail_l):
        case_result = "Petition Allowed"
    elif re.search(r"partly\s+allowed", tail_l):
        case_result = "Partly Allowed"
    elif re.search(r"settlement|compromise|mutual\s+consent", tail_l):
        case_result = "Settlement Ordered"
    elif re.search(r"bail\s+granted|bail\s+allowed", tail_l):
        case_result = "Bail Granted"
    elif re.search(r"\bacquitted\b", tail_l):
        case_result = "Acquittal"
    elif re.search(r"\bconvicted\b", tail_l):
        case_result = "Conviction"
    elif re.search(r"\bremanded\b", tail_l):
        case_result = "Case Remanded"
    elif re.search(r"maintenance.*enhanced|enhanced.*maintenance", tail_l):
        case_result = "Maintenance Enhanced"
    elif re.search(r"maintenance\s+(?:awarded|granted|fixed)", tail_l):
        case_result = "Maintenance Awarded"
    elif re.search(r"dismissed|rejected", tail_l):
        case_result = "Petition Dismissed"

    # ══ 23. PENALTY / FINE ═════════════════════════════════════
    penalty = "None"
    fine_m = re.search(
        r"(?:fine|penalty|cost)\s+of\s+Rs\.?\s*([\d,]+)",
        tail, re.IGNORECASE,
    )
    if fine_m:
        penalty = f"Rs.{fine_m.group(1)} fine/cost"

    # ══ 24. COMPENSATION / DAMAGES ════════════════════════════
    compensation = "None"
    comp_m = re.search(
        r"(?:compensation|damages|amount)\s+of\s+Rs\.?\s*([\d,]+)",
        tail, re.IGNORECASE,
    )
    if comp_m:
        compensation = f"Rs.{comp_m.group(1)}"

    # ══ 25. LEGAL AREA ═════════════════════════════════════════
    legal_area = "Domestic Violence"
    if re.search(r"MAINTENANCE|125\s*CRPC|125\s*BNSS", upper):
        legal_area = "Maintenance"
    elif re.search(r"BAIL|ANTICIPATORY", upper):
        legal_area = "Bail"
    elif re.search(r"WORKPLACE|POSH|SEXUAL\s+HARASSMENT", upper):
        legal_area = "Workplace Harassment"
    elif re.search(r"CYBER|IT\s+ACT", upper):
        legal_area = "Cyber Crime"

    # ══ 26. JUDGEMENT SUMMARY (clean, 1-2 sentences) ══════════
    raw_end = _c(tail, 2000)
    sent_m  = re.search(r"([A-Z][^.!?]{40,300}[.!?])", raw_end)
    judgement_summary = sent_m.group(1).strip() if sent_m else raw_end[:250].strip()

    # ══ BUILD RAG TEXT — all fields, one per line ══════════════
    rag_text = (
        f"Case          : {case_name}\n"
        f"Petitioner    : {petitioner}\n"
        f"Respondent    : {respondent}\n"
        f"Filed By      : {filed_by}\n"
        f"Filed Against : {filed_against}\n"
        f"Appeal No.    : {appeal_number}\n"
        f"FIR No.       : {fir_number}\n"
        f"Police Station: {police_station}\n"
        f"Court         : {court}\n"
        f"Judge         : {judge_name}\n"
        f"CNR           : {cnr}\n"
        f"Year          : {year}\n"
        f"Filing Date   : {filing_date_str}\n"
        f"Decision Date : {decision_date_str}\n"
        f"Duration      : {duration}\n"
        f"Result        : {case_result}\n"
        f"Legal Area    : {legal_area}\n"
        f"Allegations   : {'; '.join(allegations)}\n"
        f"Laws Cited    : {', '.join(cited_sections[:8])}\n"
        f"Bail Status   : {bail_status}\n"
        f"Interim Relief: {interim_relief}\n"
        f"Maintenance   : Rs.{maintenance_rs}/month\n"
        f"Penalty       : {penalty}\n"
        f"Compensation  : {compensation}\n"
        f"Witnesses     : {witness_count}\n"
        f"Evidence      : {'; '.join(evidence_types)}\n"
        f"Pet. Claims   : {petitioner_claims[:200]}\n"
        f"Res. Claims   : {respondent_claims[:200]}\n"
        f"Court Note    : {court_observations[:300]}\n"
        f"Final Order   : {final_order[:300]}\n"
        f"Summary       : {judgement_summary}"
    )

    return {
        "id":   safe_id(filename, idx),
        "text": rag_text,
        "metadata": {
            # ── Parties ──────────────────────────────
            "case_name":           case_name,
            "petitioner":          petitioner,
            "respondent":          respondent,
            "filed_by":            filed_by,
            "filed_against":       filed_against,
            # ── Case identifiers ─────────────────────
            "appeal_number":       appeal_number,
            "fir_number":          fir_number,
            "police_station":      police_station,
            "cnr_number":          cnr,
            # ── Court & Officials ────────────────────
            "court":               court,
            "judge_name":          judge_name,
            # ── Dates & Duration ─────────────────────
            "year":                year,
            "filing_date":         filing_date_str,
            "decision_date":       decision_date_str,
            "duration":            duration,
            # ── Outcome ──────────────────────────────
            "case_result":         case_result,
            "bail_status":         bail_status,
            "interim_relief":      interim_relief,
            "penalty":             penalty,
            "compensation":        compensation,
            "maintenance_rs":      maintenance_rs,
            # ── Legal classification ─────────────────
            "legal_area":          legal_area,
            "allegations":         allegations,          # list[str] ✓
            "case_laws":           cited_sections[:10],  # list[str] ✓
            # ── Evidence & witnesses ─────────────────
            "witness_count":       witness_count,
            "evidence_types":      evidence_types,       # list[str] ✓
            # ── Arguments & Observations ─────────────
            "petitioner_claims":   petitioner_claims[:300],
            "respondent_claims":   respondent_claims[:300],
            "court_observations":  court_observations[:400],
            "final_order":         final_order[:400],
            # ── Summary ──────────────────────────────
            "source_file":         filename,
            "judgement_summary":   judgement_summary,
        },
    }


# ─────────────────── Main ───────────────────────────────────────

def main():
    if not PDF_DIR.exists():
        logger.error(f"PDF directory not found: {PDF_DIR}")
        return

    # Deduplicate by file size
    seen_sizes, unique_pdfs = set(), []
    for p in sorted(PDF_DIR.glob("*.pdf")):
        sz = p.stat().st_size
        if sz not in seen_sizes:
            seen_sizes.add(sz)
            unique_pdfs.append(p)

    total_raw = len(list(PDF_DIR.glob("*.pdf")))
    logger.info(f"Found {total_raw} total PDFs → {len(unique_pdfs)} unique (after dedup).")

    records = []
    auto_duration_count = 0
    for idx, pdf_path in enumerate(tqdm(unique_pdfs, desc="Deep-extracting PDFs")):
        text = extract_full_text(pdf_path)
        if not text:
            logger.warning(f"  Skipped (no text): {pdf_path.name}")
            continue
        record = parse_case(text, pdf_path.name, idx)
        records.append(record)
        # Track auto-computed durations
        dur = record["metadata"]["duration"]
        if "days total" in dur:
            auto_duration_count += 1

    logger.info(f"Extracted {len(records)} case records.")
    logger.info(f"Auto-computed durations from dates: {auto_duration_count} cases")

    # ── Save JSONL ────────────────────────────────────────────
    with open(PINECONE_OUTPUT, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, indent=2, ensure_ascii=False) + "\n\n")
    logger.info(f"✅ Pinecone JSONL saved → {PINECONE_OUTPUT}  ({len(records)} records)")

    # ── Save standard JSON ─────────────────────────────────────
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ Standard JSON   saved → {JSON_OUTPUT}")

    # ── Sample preview ─────────────────────────────────────────
    if records:
        s = records[0]
        logger.info(f"\n{'='*60}\nSAMPLE RECORD TEXT BLOCK:\n{'='*60}")
        logger.info(s["text"])
        logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    main()
