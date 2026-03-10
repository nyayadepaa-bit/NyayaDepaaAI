"""
case_analysis/reasoning.py
---------------------------
Legal reasoning module. Analyzes retrieved cases to identify patterns,
extract legal principles, and build evidence-based explanations.
All reasoning is grounded in the retrieved cases ONLY.
"""

import logging
from collections import Counter

logger = logging.getLogger(__name__)


def analyze_patterns(similar_cases: list[dict]) -> dict:
    """
    Analyze retrieved cases to find patterns across facts, laws, and outcomes.

    Args:
        similar_cases: List of retrieved cases from the vector store

    Returns:
        Dictionary with pattern analysis
    """
    if not similar_cases:
        return {"patterns": [], "legal_areas": {}, "top_laws": [], "court_distribution": {}}

    # Legal area distribution
    area_counts = Counter(c.get("legal_area", "Unknown") for c in similar_cases)

    # Court distribution
    court_counts = Counter(c.get("court", "Unknown") for c in similar_cases)

    # Most cited laws (from case_laws metadata stored as comma-separated string)
    law_counter = Counter()
    for c in similar_cases:
        laws_str = c.get("case_laws", "")
        if laws_str:
            for law in laws_str.split(","):
                law = law.strip()
                if law:
                    law_counter[law] += 1

    # Outcome patterns
    outcome_counts = Counter(c.get("case_result", "Unknown") for c in similar_cases)
    majority_outcome = outcome_counts.most_common(1)[0] if outcome_counts else None

    # Year range
    years = [int(c["year"]) for c in similar_cases if c.get("year")]
    year_range = (min(years), max(years)) if years else None

    # Average similarity
    avg_similarity = (
        sum(c.get("similarity_score", 0) for c in similar_cases) / len(similar_cases)
    )

    return {
        "dominant_legal_area": area_counts.most_common(1)[0][0] if area_counts else "Unknown",
        "legal_areas": dict(area_counts),
        "court_distribution": dict(court_counts),
        "top_laws": [law for law, _ in law_counter.most_common(5)],
        "majority_outcome": majority_outcome[0] if majority_outcome else "Unknown",
        "outcome_distribution": dict(outcome_counts),
        "year_range": year_range,
        "avg_similarity": round(avg_similarity, 3),
        "total_precedents": len(similar_cases),
    }


def extract_judge_statements(similar_cases: list[dict], top_outcome: str) -> list[str]:
    """
    Extract possible judge statements from the judgement summaries of cases
    that match the predicted top outcome.
    """
    statements = []
    seen = set()
    
    # Filter cases that match the top outcome (fallback to all if none exactly match)
    relevant_cases = [c for c in similar_cases if c.get("case_result") == top_outcome]
    if not relevant_cases:
        relevant_cases = similar_cases
        
    for case in relevant_cases:
        summary = case.get("judgement_summary", case.get("case_summary", ""))
        if summary:
            import re
            # Split by period but keep the period
            sentences = [s.strip() + "." for s in re.split(r'\.\s+', summary) if len(s.strip()) > 15]
            
            # Keywords indicating a judicial ruling or finding
            keywords = [
                "court", "held", "ruled", "ordered", "dismissed", "granted", 
                "directed", "liable", "guilty", "acquitted", "decreed", "allowed",
                "finding", "adjudged", "concluded", "stated", "observed"
            ]
            
            found_statement = False
            for s in sentences:
                lower_s = s.lower()
                if any(w in lower_s for w in keywords):
                    if s not in seen:
                        seen.add(s)
                        statements.append(f'"{s}" — {case.get("court", "Court")} ({case.get("year", "Year")})')
                        found_statement = True
                        break  # one good statement per case
            
            # Fallback: if no keyword matched, just take the last sentence of the summary
            if not found_statement and sentences:
                s = sentences[-1]
                if s not in seen:
                    seen.add(s)
                    statements.append(f'"{s}" — {case.get("court", "Court")} ({case.get("year", "Year")})')

    return statements[:4]


def build_reasoning_text(
    user_description: str,
    similar_cases: list[dict],
    predictions: dict,
    patterns: dict,
) -> str:
    """
    Build a structured evidence-based legal reasoning explanation.
    ONLY references retrieved cases — no hallucination.

    Args:
        user_description: Original user case description
        similar_cases: Retrieved similar cases
        predictions: Output from predictor.predict_outcomes()
        patterns: Output from analyze_patterns()

    Returns:
        Formatted reasoning string
    """
    if not similar_cases:
        return "Insufficient precedent data found for this case description. Please provide more specific details."

    lines = []

    # --- Case Analysis Summary ---
    lines.append("📋 CASE ANALYSIS SUMMARY")
    lines.append("─" * 50)
    top_area = patterns.get("dominant_legal_area", "General")
    lines.append(f"Your case most closely falls under **{top_area}** based on {patterns['total_precedents']} retrieved precedents.")
    lines.append(f"Average similarity to retrieved cases: **{round(patterns['avg_similarity'] * 100, 1)}%**")
    lines.append("")

    # --- Applicable Laws ---
    top_laws = patterns.get("top_laws", [])
    if top_laws:
        lines.append("⚖️ APPLICABLE LAWS FROM PRECEDENTS")
        lines.append("─" * 50)
        for law in top_laws:
            lines.append(f"• {law}")
        lines.append("")

    # --- Precedent Analysis ---
    lines.append("📚 PRECEDENT ANALYSIS")
    lines.append("─" * 50)
    for i, case in enumerate(similar_cases[:5], 1):
        name = case.get("case_name", "Unknown Case")
        court = case.get("court", "Unknown Court")
        year = case.get("year", "")
        result = case.get("case_result", "Unknown")
        sim = round(case.get("similarity_score", 0) * 100, 1)
        summary = case.get("judgement_summary", case.get("case_summary", "No summary available."))
        lines.append(f"{i}. **{name}** ({court}, {year})")
        lines.append(f"   Similarity: {sim}% | Outcome: **{result}**")
        if summary:
            lines.append(f"   Judgement: {summary[:250]}{'...' if len(summary) > 250 else ''}")
        lines.append("")

    # --- Outcome Prediction Basis ---
    pred_list = predictions.get("predictions", [])
    if pred_list:
        lines.append("🔮 PREDICTION BASIS")
        lines.append("─" * 50)
        top_outcome = predictions.get("top_outcome", "Unknown")
        conf = round(predictions.get("confidence_score", 0) * 100, 1)
        lines.append(f"Based on the weighted analysis of {patterns['total_precedents']} precedents,")
        lines.append(f"the most likely outcome is **{top_outcome}** (confidence: {conf}%).")
        lines.append("")
        lines.append("This prediction is derived exclusively from the following precedent outcomes:")
        for p in pred_list[:4]:
            lines.append(f"• {p['outcome']}: {p['probability']}% (from {p['count']} case(s))")
        lines.append("")

    # --- Court Hierarchy Note ---
    court_dist = patterns.get("court_distribution", {})
    if court_dist:
        lines.append("🏛️ COURT HIERARCHY ANALYSIS")
        lines.append("─" * 50)
        lines.append("Precedents retrieved from the following courts (higher courts carry more weight):")
        for court, count in sorted(court_dist.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"• {court}: {count} case(s)")
        lines.append("")

    # --- Disclaimer ---
    lines.append("─" * 50)
    lines.append("⚠️ IMPORTANT DISCLAIMER")
    lines.append("This analysis is based solely on retrieved legal precedents and is for informational purposes only. It does not constitute legal advice. Outcome predictions are probabilistic estimates derived from historical case patterns. Consult a qualified advocate for your specific situation.")

    return "\n".join(lines)
