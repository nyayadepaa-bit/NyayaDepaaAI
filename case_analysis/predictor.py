"""
case_analysis/predictor.py
---------------------------
Outcome prediction engine using court-hierarchy-weighted precedent frequency.
Calculates probability of each outcome type from retrieved similar cases.
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Court hierarchy weights
COURT_WEIGHTS = {
    "supreme court": 1.0,
    "supreme court of india": 1.0,
    "high court": 0.7,
    "district court": 0.4,
    "sessions court": 0.4,
    "family court": 0.4,
    "magistrate court": 0.35,
    "tribunal": 0.5,
    "national company law": 0.6,
    "consumer forum": 0.35,
}

# Normalize result strings to standard outcome labels
OUTCOME_NORMALIZER = {
    "petition allowed": "Petition Allowed",
    "appeal allowed": "Petition Allowed",
    "allowed": "Petition Allowed",
    "petition partly allowed": "Petition Partly Allowed",
    "partly allowed": "Petition Partly Allowed",
    "petition dismissed": "Petition Dismissed",
    "appeal dismissed": "Petition Dismissed",
    "dismissed": "Petition Dismissed",
    "settlement ordered": "Settlement Ordered",
    "settlement": "Settlement Ordered",
    "compensation granted": "Compensation Granted",
    "compensation awarded": "Compensation Granted",
    "case remanded": "Case Remanded",
    "remanded": "Case Remanded",
    "remanded for retrial": "Case Remanded",
    "interim relief granted": "Interim Relief Granted",
    "interim relief": "Interim Relief Granted",
    "acquitted": "Acquittal",
    "convicted": "Conviction",
    "bail granted": "Bail Granted",
    "bail rejected": "Bail Rejected",
    "stay granted": "Stay Granted",
    "injunction granted": "Injunction Granted",
}


def get_court_weight(court: str) -> float:
    """Return the weight for a given court name."""
    court_lower = court.lower()
    for key, weight in COURT_WEIGHTS.items():
        if key in court_lower:
            return weight
    return 0.4  # Default for unrecognized courts


def normalize_outcome(result: str) -> str:
    """Map a case_result string to a normalized outcome label."""
    r = result.strip().lower()
    for key, label in OUTCOME_NORMALIZER.items():
        if key in r:
            return label
    return result.strip().title()  # Return capitalized as-is if no match


def predict_outcomes(similar_cases: list[dict]) -> dict:
    """
    Predict outcome probabilities using court-weighted precedent frequency.

    Args:
        similar_cases: List of retrieved case dicts with similarity_score + metadata

    Returns:
        {
            "predictions": [{"outcome": str, "probability": float, "count": int, "weighted_count": float}],
            "total_weight": float,
            "top_outcome": str,
            "confidence_score": float,
        }
    """
    if not similar_cases:
        return {
            "predictions": [],
            "total_weight": 0.0,
            "top_outcome": "Insufficient Data",
            "confidence_score": 0.0,
        }

    outcome_weights = defaultdict(float)
    outcome_counts = defaultdict(int)

    for case in similar_cases:
        raw_result = case.get("case_result", "")
        if not raw_result:
            continue

        outcome = normalize_outcome(raw_result)
        court = case.get("court", "")
        court_weight = get_court_weight(court)
        similarity = case.get("similarity_score", 0.5)

        # Combined weight = court_weight * similarity_boost
        combined_weight = court_weight * (0.5 + 0.5 * similarity)

        outcome_weights[outcome] += combined_weight
        outcome_counts[outcome] += 1

    total_weight = sum(outcome_weights.values())

    if total_weight == 0:
        return {
            "predictions": [],
            "total_weight": 0.0,
            "top_outcome": "Insufficient Data",
            "confidence_score": 0.0,
        }

    predictions = []
    for outcome, weight in sorted(outcome_weights.items(), key=lambda x: x[1], reverse=True):
        probability = round((weight / total_weight) * 100, 1)
        predictions.append({
            "outcome": outcome,
            "probability": probability,
            "count": outcome_counts[outcome],
            "weighted_count": round(weight, 3),
        })

    top_outcome = predictions[0]["outcome"] if predictions else "Unknown"
    top_prob = predictions[0]["probability"] if predictions else 0.0

    # Confidence: higher if top outcome dominates and similarity scores are high
    avg_similarity = sum(c.get("similarity_score", 0) for c in similar_cases) / len(similar_cases)
    confidence_score = round(min(1.0, (top_prob / 100) * 0.6 + avg_similarity * 0.4), 3)

    return {
        "predictions": predictions,
        "total_weight": round(total_weight, 3),
        "top_outcome": top_outcome,
        "confidence_score": confidence_score,
    }
