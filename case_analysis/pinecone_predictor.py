"""
case_analysis/pinecone_predictor.py
------------------------------------
Pinecone-based Legal Case Prediction Engine.

Analyzes cases retrieved from Pinecone to produce:
  - Multi-condition analysis (individual + collective factor evaluation)
  - Outcome predictions with probability estimates
  - Estimated case duration from historical patterns
  - Strategic advantages / disadvantages
  - Personalized legal reasoning

All predictions are strictly derived from Pinecone-retrieved data.
No case names or identifiers are exposed to the user.
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


# ── Court hierarchy weights for prediction ──────────────────────
COURT_WEIGHTS = {
    "supreme court": 1.0,
    "supreme court of india": 1.0,
    "high court": 0.75,
    "sessions court": 0.45,
    "district court": 0.40,
    "family court": 0.40,
    "judicial magistrate": 0.35,
    "magistrate court": 0.35,
    "tribunal": 0.50,
    "consumer forum": 0.35,
}

# ── Outcome normalization ───────────────────────────────────────
OUTCOME_MAP = {
    "petition allowed": "Petition Allowed",
    "appeal allowed": "Petition Allowed",
    "application allowed": "Petition Allowed",
    "allowed": "Petition Allowed",
    "partly allowed": "Partly Allowed",
    "petition partly allowed": "Partly Allowed",
    "petition dismissed": "Petition Dismissed",
    "appeal dismissed": "Petition Dismissed",
    "dismissed": "Petition Dismissed",
    "rejected": "Petition Dismissed",
    "settlement ordered": "Settlement / Compromise",
    "settlement": "Settlement / Compromise",
    "compromise": "Settlement / Compromise",
    "acquittal": "Acquittal",
    "acquitted": "Acquittal",
    "conviction": "Conviction",
    "convicted": "Conviction",
    "bail granted": "Bail Granted",
    "bail rejected": "Bail Rejected",
    "maintenance awarded": "Maintenance Awarded",
    "maintenance enhanced": "Maintenance Enhanced",
    "case remanded": "Case Remanded",
    "remanded": "Case Remanded",
}


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _court_weight(court_name: str) -> float:
    """Return a weight [0-1] based on the court hierarchy."""
    lower = court_name.lower()
    for key, w in COURT_WEIGHTS.items():
        if key in lower:
            return w
    return 0.40


def _normalize_outcome(raw: str) -> str:
    """Map raw case_result to a normalized label."""
    lower = raw.strip().lower()
    for key, label in OUTCOME_MAP.items():
        if key in lower:
            return label
    return raw.strip().title() if raw.strip() else "Unknown"


def _parse_duration_days(duration_str: str) -> Optional[int]:
    """Extract total days from a duration string like '2Y 3M 10D (850 days total)'."""
    if not duration_str or duration_str == "Unknown":
        return None
    m = re.search(r"\((\d+)\s*days?\s*total\)", duration_str, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # Try Y/M/D components
    total = 0
    y = re.search(r"(\d+)\s*Y", duration_str)
    mo = re.search(r"(\d+)\s*M", duration_str)
    d = re.search(r"(\d+)\s*D", duration_str)
    if y:
        total += int(y.group(1)) * 365
    if mo:
        total += int(mo.group(1)) * 30
    if d:
        total += int(d.group(1))
    return total if total > 0 else None


def _extract_legal_conditions(query: str) -> list[str]:
    """
    Extract distinct legal conditions / factors from the user's case description.
    Returns a list of identified factors for multi-condition analysis.
    """
    factors = []

    condition_patterns = {
        "Domestic Violence / Cruelty": r"domestic\s+violence|cruelty|498\s*[Aa]|beating|physical\s+abuse|mental\s+torture",
        "Dowry Harassment": r"dowry|dahej|stridhan|gifts?\s+demand",
        "Maintenance / Alimony": r"maintenance|alimony|financial\s+support|125\s*cr\.?p\.?c",
        "Sexual Harassment": r"sexual\s+harassment|posh|unwanted\s+touch|molestation|354",
        "Rape / Sexual Assault": r"rape|sexual\s+assault|376",
        "Stalking": r"stalking|following|354\s*[Dd]",
        "Cyber Crime": r"cyber|online\s+harassment|morphed|fake\s+profile|blackmail",
        "Child Custody": r"custody|child|guardianship|visitation",
        "Property / Inheritance": r"property|inheritance|stridhan|ancestral|succession",
        "Divorce / Separation": r"divorce|separation|mutual\s+consent|matrimonial",
        "FIR / Police Complaint": r"fir|police\s+complaint|first\s+information|reported\s+to\s+police",
        "Protection Order": r"protection\s+order|restraining|residence\s+order",
        "Bail": r"bail|anticipatory\s+bail|regular\s+bail",
        "Workplace Discrimination": r"workplace|discrimination|unfair\s+termination|wrongful",
        "Evidence Available": r"evidence|medical\s+report|photograph|cctv|witness|proof|document",
        "Threat / Intimidation": r"threat|intimidat|blackmail|extort",
        "Minor Victim": r"minor|child\s+victim|below\s*18|underage",
    }

    lower_query = query.lower()
    for label, pattern in condition_patterns.items():
        if re.search(pattern, lower_query, re.IGNORECASE):
            factors.append(label)

    if not factors:
        factors.append("General Legal Matter")

    return factors


# ═══════════════════════════════════════════════════════════════
#  MAIN PREDICTION ENGINE
# ═══════════════════════════════════════════════════════════════

class PineconePredictionEngine:
    """
    Analyzes Pinecone-retrieved cases to produce structured predictions.
    Strictly grounded in retrieved data — no hallucination.
    """

    def predict(
        self,
        user_query: str,
        retrieved_cases: list[dict],
        user_profile: Optional[dict] = None,
    ) -> dict:
        """
        Produce a comprehensive prediction from retrieved Pinecone cases.

        Args:
            user_query: The user's legal case description
            retrieved_cases: List of case dicts from retrieval.retriever.retrieve()
            user_profile: Optional user profile dict

        Returns:
            Structured prediction dict with all analysis sections
        """
        if not retrieved_cases:
            return self._empty_prediction("No matching cases retrieved from database.")

        # ─── 1. Multi-Condition Factor Analysis ───────────
        user_factors = _extract_legal_conditions(user_query)
        factor_analysis = self._analyze_factors(user_factors, retrieved_cases)

        # ─── 2. Outcome Predictions ───────────────────────
        outcome_predictions = self._predict_outcomes(retrieved_cases)

        # ─── 3. Duration Estimation ───────────────────────
        duration_estimate = self._estimate_duration(retrieved_cases)

        # ─── 4. Strategic Analysis ────────────────────────
        strategic = self._strategic_analysis(
            retrieved_cases, outcome_predictions, user_factors
        )

        # ─── 5. Judge Reasoning Patterns ──────────────────
        judge_reasoning_patterns = self._extract_judge_reasoning(
            retrieved_cases, outcome_predictions
        )

        # ─── 6. Confidence Score ──────────────────────────
        confidence = self._compute_confidence(
            retrieved_cases, outcome_predictions, factor_analysis
        )

        # ─── 7. Build LLM-enrichment context ─────────────
        # This context block is injected into the LLM prompt so it can
        # generate personalized reasoning WITHOUT revealing case names
        enrichment_context = self._build_enrichment_context(
            factor_analysis, outcome_predictions,
            duration_estimate, strategic, confidence,
            judge_reasoning_patterns
        )

        return {
            "user_factors": user_factors,
            "factor_analysis": factor_analysis,
            "outcome_predictions": outcome_predictions,
            "duration_estimate": duration_estimate,
            "strategic_analysis": strategic,
            "judge_reasoning_patterns": judge_reasoning_patterns,
            "confidence_score": confidence,
            "n_cases_analyzed": len(retrieved_cases),
            "enrichment_context": enrichment_context,
            "error": None,
        }

    # ─── Factor-by-factor analysis ────────────────────────────

    def _analyze_factors(
        self, user_factors: list[str], cases: list[dict]
    ) -> list[dict]:
        """
        For each user factor, find matching case conditions and their outcomes.
        """
        factor_results = []

        for factor in user_factors:
            matching_cases = self._filter_cases_by_factor(factor, cases)
            if not matching_cases:
                factor_results.append({
                    "factor": factor,
                    "matched_cases": 0,
                    "dominant_outcome": "Insufficient Data",
                    "outcome_distribution": {},
                    "avg_similarity": 0.0,
                })
                continue

            outcomes = Counter()
            total_sim = 0.0
            for c in matching_cases:
                raw_result = c.get("case_result", "")
                if raw_result:
                    outcomes[_normalize_outcome(raw_result)] += 1
                total_sim += c.get("score", c.get("combined_score", 0.5))

            dominant = outcomes.most_common(1)[0][0] if outcomes else "Unknown"
            avg_sim = total_sim / len(matching_cases) if matching_cases else 0

            factor_results.append({
                "factor": factor,
                "matched_cases": len(matching_cases),
                "dominant_outcome": dominant,
                "outcome_distribution": dict(outcomes),
                "avg_similarity": round(avg_sim, 3),
            })

        return factor_results

    def _filter_cases_by_factor(
        self, factor: str, cases: list[dict]
    ) -> list[dict]:
        """Filter retrieved cases that are relevant to a specific legal factor."""
        # Map factor labels to search terms in case text/metadata
        factor_keywords = {
            "Domestic Violence / Cruelty": ["498a", "cruelty", "domestic violence", "pwdva", "dv act"],
            "Dowry Harassment": ["dowry", "dahej", "stridhan", "304b"],
            "Maintenance / Alimony": ["maintenance", "alimony", "125 crpc", "125 bnss"],
            "Sexual Harassment": ["sexual harassment", "posh", "354", "molestation"],
            "Rape / Sexual Assault": ["rape", "376", "sexual assault"],
            "Stalking": ["stalking", "354d"],
            "Cyber Crime": ["cyber", "it act", "66a", "67"],
            "Child Custody": ["custody", "guardian", "child"],
            "Property / Inheritance": ["property", "inheritance", "succession", "stridhan"],
            "Divorce / Separation": ["divorce", "separation", "matrimonial", "mutual consent"],
            "FIR / Police Complaint": ["fir", "police", "complaint"],
            "Protection Order": ["protection order", "residence order", "restraining"],
            "Bail": ["bail", "anticipatory"],
            "Workplace Discrimination": ["workplace", "discrimination", "termination"],
            "Evidence Available": ["evidence", "medical", "photograph", "witness"],
            "Threat / Intimidation": ["threat", "intimidat", "blackmail"],
            "Minor Victim": ["minor", "child victim", "juvenile"],
        }

        keywords = factor_keywords.get(factor, [factor.lower()])
        matched = []

        for c in cases:
            text = (c.get("text", "") + " " + c.get("legal_category", "")).lower()
            if any(kw in text for kw in keywords):
                matched.append(c)

        # If factor filtering is too strict, return all cases
        if not matched:
            return cases

        return matched

    # ─── Outcome Prediction ───────────────────────────────────

    def _predict_outcomes(self, cases: list[dict]) -> dict:
        """
        Weighted outcome predictions based on court hierarchy + similarity.
        """
        outcome_weights = defaultdict(float)
        outcome_counts = defaultdict(int)

        for c in cases:
            raw_result = c.get("case_result", "")
            if not raw_result:
                continue

            outcome = _normalize_outcome(raw_result)
            court = c.get("court", "")
            cw = _court_weight(court)
            similarity = c.get("score", c.get("combined_score", 0.5))

            weight = cw * (0.4 + 0.6 * similarity)
            outcome_weights[outcome] += weight
            outcome_counts[outcome] += 1

        total_w = sum(outcome_weights.values())
        if total_w == 0:
            return {
                "predictions": [],
                "top_outcome": "Insufficient Data",
                "top_probability": 0.0,
            }

        predictions = []
        for outcome, w in sorted(outcome_weights.items(), key=lambda x: x[1], reverse=True):
            prob = round((w / total_w) * 100, 1)
            predictions.append({
                "outcome": outcome,
                "probability": prob,
                "count": outcome_counts[outcome],
                "weighted_score": round(w, 3),
            })

        return {
            "predictions": predictions,
            "top_outcome": predictions[0]["outcome"],
            "top_probability": predictions[0]["probability"],
        }

    # ─── Duration Estimation ──────────────────────────────────

    def _estimate_duration(self, cases: list[dict]) -> dict:
        """
        Estimate case duration from retrieved cases' duration metadata.
        """
        durations_days = []

        for c in cases:
            dur_str = c.get("duration", "")
            days = _parse_duration_days(dur_str)
            if days and 1 <= days <= 10000:
                durations_days.append(days)

        if not durations_days:
            # Fallback: try to infer from filing_date / decision_date
            for c in cases:
                filing = c.get("filing_date", "")
                decision = c.get("decision_date", "")
                if filing and decision and filing != "Unknown" and decision != "Unknown":
                    # Rough parse
                    try:
                        from datetime import datetime
                        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]:
                            try:
                                fd = datetime.strptime(filing.strip(), fmt)
                                dd = datetime.strptime(decision.strip(), fmt)
                                delta = abs((dd - fd).days)
                                if 1 <= delta <= 10000:
                                    durations_days.append(delta)
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass

        if not durations_days:
            return {
                "min_months": None,
                "max_months": None,
                "avg_months": None,
                "median_months": None,
                "estimate_text": "Duration data insufficient from retrieved cases. Typical Indian court proceedings range from 6 months to 3 years depending on court level and complexity.",
                "data_points": 0,
            }

        durations_days.sort()
        avg_days = sum(durations_days) / len(durations_days)
        median_days = durations_days[len(durations_days) // 2]
        min_days = durations_days[0]
        max_days = durations_days[-1]

        def days_to_text(d):
            if d < 30:
                return f"{d} days"
            months = d / 30
            if months < 12:
                return f"{months:.0f} months"
            years = months / 12
            rem = months % 12
            if rem < 1:
                return f"{years:.0f} year(s)"
            return f"{years:.0f} year(s) {rem:.0f} month(s)"

        estimate_text = (
            f"Based on {len(durations_days)} similar cases, estimated duration is "
            f"**{days_to_text(min_days)}** to **{days_to_text(max_days)}** "
            f"(average: {days_to_text(int(avg_days))}, median: {days_to_text(median_days)}). "
        )

        # Add qualifiers
        if avg_days < 180:
            estimate_text += "Cases of this nature tend to resolve relatively quickly."
        elif avg_days < 730:
            estimate_text += "This is within the typical range for such legal matters."
        else:
            estimate_text += "Cases of this complexity often take extended periods — legal persistence and proper documentation are key."

        return {
            "min_months": round(min_days / 30, 1),
            "max_months": round(max_days / 30, 1),
            "avg_months": round(avg_days / 30, 1),
            "median_months": round(median_days / 30, 1),
            "estimate_text": estimate_text,
            "data_points": len(durations_days),
        }

    # ─── Strategic Analysis ───────────────────────────────────

    def _strategic_analysis(
        self,
        cases: list[dict],
        predictions: dict,
        user_factors: list[str],
    ) -> dict:
        """
        Identify strategic advantages, risks, and recommendations
        based on retrieved case patterns.
        """
        advantages = []
        risks = []
        recommendations = []

        # Analyze evidence patterns
        evidence_types = Counter()
        for c in cases:
            ev = c.get("text", "")
            if "medical" in ev.lower():
                evidence_types["Medical Evidence"] += 1
            if "photograph" in ev.lower() or "cctv" in ev.lower():
                evidence_types["Photo/Video Evidence"] += 1
            if "witness" in ev.lower():
                evidence_types["Witness Testimony"] += 1
            if "fir" in ev.lower() or "first information" in ev.lower():
                evidence_types["FIR Filed"] += 1
            if "whatsapp" in ev.lower() or "message" in ev.lower() or "chat" in ev.lower():
                evidence_types["Digital Communication"] += 1
            if "affidavit" in ev.lower():
                evidence_types["Affidavit"] += 1

        # Evidence-based advantages
        for ev_type, count in evidence_types.most_common():
            pct = round(count / len(cases) * 100)
            if pct >= 40:
                advantages.append(
                    f"In {pct}% of similar cases, **{ev_type}** was present and strengthened the petitioner's position."
                )

        # Outcome-based strategic insights
        top_outcome = predictions.get("top_outcome", "")
        top_prob = predictions.get("top_probability", 0)

        if top_prob >= 60:
            advantages.append(
                f"Historical patterns strongly favor **{top_outcome}** ({top_prob}% probability) in similar fact situations."
            )
        elif top_prob >= 40:
            recommendations.append(
                f"The most likely outcome is {top_outcome} ({top_prob}%), but alternative outcomes have significant probability. Strong evidence is critical."
            )

        # Risk: multiple outcomes are close
        preds_list = predictions.get("predictions", [])
        if len(preds_list) >= 2:
            gap = preds_list[0]["probability"] - preds_list[1]["probability"]
            if gap < 15:
                risks.append(
                    f"The gap between the top two outcomes is only {gap:.0f}% — the case could go either way. Quality of evidence and legal representation will be decisive."
                )

        # Factor-based risks
        if "Domestic Violence / Cruelty" in user_factors and "Dowry Harassment" in user_factors:
            advantages.append(
                "Cases involving both domestic violence and dowry harassment have stronger statutory protections (PWDVA 2005 + Sec 498A IPC/BNS)."
            )
        if "FIR / Police Complaint" in user_factors:
            advantages.append(
                "Having a filed FIR significantly strengthens the legal position — courts give weight to timely reporting."
            )
        if "Evidence Available" in user_factors:
            advantages.append(
                "Documented evidence (medical reports, photos, messages) substantially increases the probability of a favorable outcome."
            )
        if "Minor Victim" in user_factors:
            advantages.append(
                "Cases involving minor victims receive expedited attention and stricter penalties under POCSO Act."
            )

        # General risks
        if "Evidence Available" not in user_factors:
            risks.append(
                "Without documented evidence, the case relies heavily on oral testimony — courts may require corroboration."
            )

        # Court-level recommendations
        court_levels = Counter()
        for c in cases:
            court = c.get("court", "").lower()
            for key in COURT_WEIGHTS:
                if key in court:
                    court_levels[key] += 1
                    break

        if court_levels:
            top_court = court_levels.most_common(1)[0][0].title()
            recommendations.append(
                f"Similar cases are predominantly handled at the **{top_court}** level. Filing at the appropriate court level is important for efficient resolution."
            )

        # Law-specific recommendations
        laws_cited = Counter()
        for c in cases:
            text = c.get("text", "")
            for law_pattern, law_name in [
                (r"498\s*[Aa]", "Section 498A IPC (Cruelty)"),
                (r"PWDVA|D\.V\.\s*Act|Protection.*Domestic.*Violence", "PWDVA 2005"),
                (r"125\s*Cr\.?P\.?C|125\s*BNSS", "Section 125 CrPC/BNSS (Maintenance)"),
                (r"354", "Section 354 IPC (Outraging Modesty)"),
                (r"376", "Section 376 IPC (Rape)"),
                (r"POSH", "POSH Act 2013"),
                (r"304\s*[Bb]", "Section 304B IPC (Dowry Death)"),
            ]:
                if re.search(law_pattern, text, re.IGNORECASE):
                    laws_cited[law_name] += 1

        if laws_cited:
            top_laws = [f"**{law}**" for law, _ in laws_cited.most_common(3)]
            recommendations.append(
                f"The most frequently applied laws in similar cases are {', '.join(top_laws)}. Ensure your advocate files under the applicable sections."
            )

        # Maintenance-related insights
        maintenance_amounts = []
        for c in cases:
            maint = c.get("maintenance_rs", 0)
            if isinstance(maint, (int, float)) and maint > 0:
                maintenance_amounts.append(maint)

        if maintenance_amounts:
            avg_m = sum(maintenance_amounts) / len(maintenance_amounts)
            min_m = min(maintenance_amounts)
            max_m = max(maintenance_amounts)
            if avg_m > 0:
                recommendations.append(
                    f"Maintenance awards in similar cases range from **Rs.{min_m:,.0f}** to **Rs.{max_m:,.0f}** per month (average: Rs.{avg_m:,.0f}/month)."
                )

        return {
            "advantages": advantages[:5],
            "risks": risks[:5],
            "recommendations": recommendations[:5],
        }

    # ─── Judge Reasoning Extraction ─────────────────────────

    def _extract_judge_reasoning(
        self,
        cases: list[dict],
        predictions: dict,
    ) -> dict:
        """
        Extract judge reasoning patterns from retrieved cases.
        Groups reasoning by outcome to show WHY judges decided in each direction.
        Returns structured reasoning data for both the LLM enrichment and direct output.
        """
        # Group reasoning by outcome
        outcome_reasoning: dict[str, list[dict]] = defaultdict(list)
        decision_basis_counter: Counter = Counter()

        for c in cases:
            raw_result = c.get("case_result", "")
            if not raw_result:
                continue

            outcome = _normalize_outcome(raw_result)

            # Extract reasoning from all available fields
            reasoning_text = c.get("judge_reasoning", "")
            court_obs = c.get("court_observations", "")
            final_order = c.get("final_order", "")
            summary = c.get("judgement_summary", "")
            decision_basis = c.get("decision_basis", [])
            laws = c.get("case_laws", [])
            evidence = c.get("evidence_types", [])
            allegations = c.get("allegations", [])
            court = c.get("court", "")

            # Count the decision basis categories
            if isinstance(decision_basis, list):
                for basis in decision_basis:
                    decision_basis_counter[basis] += 1

            reasoning_entry = {
                "outcome": outcome,
                "court": court,
                "laws_applied": laws if isinstance(laws, list) else [],
                "evidence_types": evidence if isinstance(evidence, list) else [],
                "allegations": allegations if isinstance(allegations, list) else [],
            }

            # Pick the best reasoning text available
            if court_obs and court_obs not in ("Not extracted", "Unknown", ""):
                reasoning_entry["court_observation"] = court_obs[:400]
            if summary and summary not in ("Not extracted", "Unknown", ""):
                reasoning_entry["summary"] = summary[:300]
            if final_order and final_order not in ("Not extracted", "Unknown", ""):
                reasoning_entry["order_excerpt"] = final_order[:300]
            if isinstance(decision_basis, list) and decision_basis:
                reasoning_entry["decision_basis"] = decision_basis

            outcome_reasoning[outcome].append(reasoning_entry)

        # Build per-outcome reasoning summaries
        reasoning_by_outcome = {}
        for outcome, entries in outcome_reasoning.items():
            # Collect all laws cited for this outcome
            all_laws = Counter()
            all_evidence = Counter()
            all_basis = Counter()
            court_observations = []
            summaries = []

            for entry in entries:
                for law in entry.get("laws_applied", []):
                    if law and law != "Unknown":
                        all_laws[law] += 1
                for ev in entry.get("evidence_types", []):
                    if ev and ev != "Unknown":
                        all_evidence[ev] += 1
                for b in entry.get("decision_basis", []):
                    all_basis[b] += 1
                if "court_observation" in entry:
                    court_observations.append(entry["court_observation"])
                if "summary" in entry:
                    summaries.append(entry["summary"])

            reasoning_by_outcome[outcome] = {
                "case_count": len(entries),
                "key_laws": [law for law, _ in all_laws.most_common(5)],
                "common_evidence": [ev for ev, _ in all_evidence.most_common(5)],
                "decision_bases": [b for b, _ in all_basis.most_common(3)],
                "court_observations": court_observations[:3],  # Top 3 most relevant
                "case_summaries": summaries[:3],
            }

        # Top decision basis across all outcomes
        top_bases = [basis for basis, _ in decision_basis_counter.most_common(5)]

        return {
            "reasoning_by_outcome": reasoning_by_outcome,
            "top_decision_bases": top_bases,
            "total_cases_with_reasoning": sum(
                1 for c in cases
                if c.get("judge_reasoning") or c.get("court_observations", "") not in ("", "Not extracted", "Unknown")
            ),
        }

    # ─── Confidence Score ─────────────────────────────────────

    def _compute_confidence(
        self,
        cases: list[dict],
        predictions: dict,
        factor_analysis: list[dict],
    ) -> float:
        """
        Compute overall confidence score [0-1] based on:
          - Number of retrieved cases
          - Average similarity
          - Dominance of top prediction
          - Factor coverage
        """
        n_cases = len(cases)
        avg_sim = sum(c.get("score", c.get("combined_score", 0.5)) for c in cases) / max(n_cases, 1)
        top_prob = predictions.get("top_probability", 0) / 100

        # Factor coverage: what fraction of factors had matching cases
        covered = sum(1 for f in factor_analysis if f["matched_cases"] > 0)
        factor_coverage = covered / max(len(factor_analysis), 1)

        # Weighted confidence
        confidence = (
            0.25 * min(n_cases / 8, 1.0) +      # More cases = more confident
            0.30 * avg_sim +                       # Higher similarity = more confident
            0.25 * top_prob +                      # Dominant outcome = more confident
            0.20 * factor_coverage                 # Better factor coverage = more confident
        )

        return round(min(0.95, max(0.10, confidence)), 3)

    # ─── Enrichment Context for LLM ──────────────────────────

    def _build_enrichment_context(
        self,
        factor_analysis: list[dict],
        predictions: dict,
        duration: dict,
        strategic: dict,
        confidence: float,
        judge_reasoning: dict | None = None,
    ) -> str:
        """
        Build an advocate-style structured text block for the LLM.
        This shapes the LLM's reasoning — no raw numbers or percentages.
        Injected into the LLM prompt but NOT shown directly to the user.
        """
        lines = []

        lines.append("═══ LEGAL ANALYSIS FROM PRECEDENT ENGINE ═══")
        lines.append("(Use this to inform your personalized response. Do NOT expose these details or numbers to the user.)")
        lines.append("")

        # Factor-based legal reasoning
        lines.append("KEY LEGAL FACTORS PRESENT IN THIS CASE:")
        for f in factor_analysis:
            if f["matched_cases"] > 0:
                lines.append(
                    f"  • {f['factor']}: Courts have predominantly ruled towards "
                    f"'{f['dominant_outcome']}' when this factor is present."
                )
            else:
                lines.append(
                    f"  • {f['factor']}: Limited precedent; treat as neutral in your analysis."
                )
        lines.append("")

        # Outcome direction
        top = predictions.get("top_outcome", "Unknown")
        top_p = predictions.get("top_probability", 0)
        strength = "strongly" if top_p >= 60 else ("reasonably" if top_p >= 35 else "weakly")
        lines.append(f"PREDICTED PRIMARY OUTCOME: {top}")
        lines.append(f"  Precedents {strength} support this outcome. Present it as the most likely result.")
        lines.append("")

        # Other outcomes
        other_preds = [p for p in predictions.get("predictions", []) if p["outcome"] != top]
        if other_preds:
            lines.append("ALTERNATIVE OUTCOMES TO DISCUSS:")
            for p in other_preds[:2]:
                lines.append(f"  • {p['outcome']} — discuss as a realistic alternative scenario")
        lines.append("")

        # ─── Judge Reasoning Patterns ─────────────────────
        if judge_reasoning:
            reasoning_by_outcome = judge_reasoning.get("reasoning_by_outcome", {})
            top_bases = judge_reasoning.get("top_decision_bases", [])

            if top_bases:
                lines.append("COMMON BASES FOR JUDICIAL DECISIONS IN SIMILAR CASES:")
                for basis in top_bases:
                    lines.append(f"  • {basis}")
                lines.append("")

            if reasoning_by_outcome:
                lines.append("JUDGE REASONING PATTERNS BY OUTCOME:")
                for outcome, data in reasoning_by_outcome.items():
                    lines.append(f"  ── {outcome} ({data['case_count']} cases) ──")
                    if data.get("decision_bases"):
                        lines.append(f"    Decision basis: {', '.join(data['decision_bases'])}")
                    if data.get("key_laws"):
                        lines.append(f"    Key laws applied: {', '.join(data['key_laws'][:4])}")
                    if data.get("common_evidence"):
                        lines.append(f"    Evidence relied upon: {', '.join(data['common_evidence'][:4])}")
                    # Include actual court observations (anonymized)
                    for obs in data.get("court_observations", [])[:2]:
                        clean = obs.replace("\n", " ").strip()[:250]
                        lines.append(f"    Court held: \"{clean}\"")
                    for summ in data.get("case_summaries", [])[:1]:
                        clean = summ.replace("\n", " ").strip()[:200]
                        lines.append(f"    Context: \"{clean}\"")
                    lines.append("")

                lines.append(
                    "INSTRUCTION: Use the above judge reasoning to explain WHY the court is likely "
                    "to decide a certain way in the user's case. Reference the legal basis, evidence "
                    "patterns, and judicial observations. Do NOT name any specific cases."
                )
                lines.append("")

        # Duration
        if duration.get("avg_months"):
            lines.append(
                f"CASE TIMELINE: Estimated {duration['min_months']:.0f} to "
                f"{duration['max_months']:.0f} months (typical for this case type)"
            )
        elif duration.get("estimate_text"):
            lines.append(f"CASE TIMELINE: {duration['estimate_text']}")
        lines.append("")

        # Strategic
        lines.append("ADVOCACY POINTS TO EMPHASIZE:")
        for a in strategic.get("advantages", []):
            lines.append(f"  ✓ {a}")
        lines.append("RISKS TO WARN THE USER ABOUT:")
        for r in strategic.get("risks", []):
            lines.append(f"  ⚠ {r}")
        lines.append("SPECIFIC RECOMMENDATIONS:")
        for r in strategic.get("recommendations", []):
            lines.append(f"  → {r}")

        lines.append("")
        lines.append("INSTRUCTION: Use the above to write a personalized, specific analysis.")
        lines.append("Do NOT mention case counts, percentages, or similarity scores to the user.")
        lines.append("Speak as their advocate. Reference THEIR specific facts and evidence.")

        return "\n".join(lines)

    # ─── Empty prediction fallback ────────────────────────────

    def _empty_prediction(self, reason: str) -> dict:
        return {
            "user_factors": [],
            "factor_analysis": [],
            "outcome_predictions": {"predictions": [], "top_outcome": "Insufficient Data", "top_probability": 0},
            "duration_estimate": {"estimate_text": "Insufficient data.", "data_points": 0},
            "strategic_analysis": {"advantages": [], "risks": [], "recommendations": []},
            "judge_reasoning_patterns": {"reasoning_by_outcome": {}, "top_decision_bases": [], "total_cases_with_reasoning": 0},
            "confidence_score": 0.0,
            "n_cases_analyzed": 0,
            "enrichment_context": "",
            "error": reason,
        }
