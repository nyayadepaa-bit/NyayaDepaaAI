"""
case_analysis/analyzer.py
--------------------------
Main pipeline orchestrator for the Legal Case Analysis System.
Coordinates: embed → retrieve → predict → reason → return.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from case_analysis.retriever import retrieve_similar
from case_analysis.predictor import predict_outcomes
from case_analysis.reasoning import analyze_patterns, build_reasoning_text
from case_analysis.case_store import collection_count
from app.config import CASE_TOP_K

logger = logging.getLogger(__name__)


class CasePipeline:
    """
    Full legal case analysis pipeline.
    Retrieves similar precedents, predicts outcomes, generates reasoning.
    """

    def analyze(
        self,
        user_description: str,
        top_k: int = None,
    ) -> dict:
        """
        Run full case analysis for a user-provided case description.

        Args:
            user_description: Free-text description of the user's legal situation
            top_k: Number of similar cases to retrieve

        Returns:
            Structured dict with: similar_cases, outcome_predictions, reasoning, confidence_score
        """
        top_k = top_k or CASE_TOP_K

        if not user_description or len(user_description.strip()) < 20:
            return {
                "error": "Please provide a more detailed case description (at least 20 characters).",
                "similar_cases": [],
                "outcome_predictions": {},
                "reasoning": "",
                "confidence_score": 0.0,
                "total_cases_in_db": collection_count(),
            }

        logger.info(f"Analyzing case: {user_description[:100]}...")

        # Step 1: Retrieve similar cases
        similar_cases = retrieve_similar(user_description, top_k=top_k)

        if not similar_cases:
            return {
                "error": "No similar cases found in the database. Ensure the case database is ingested.",
                "similar_cases": [],
                "outcome_predictions": {},
                "reasoning": "No precedents found.",
                "confidence_score": 0.0,
                "total_cases_in_db": collection_count(),
            }

        # Step 2: Predict outcomes
        prediction_result = predict_outcomes(similar_cases)

        # Step 3: Analyze patterns
        patterns = analyze_patterns(similar_cases)

        # Step 4: Build reasoning text
        reasoning_text = build_reasoning_text(
            user_description=user_description,
            similar_cases=similar_cases,
            predictions=prediction_result,
            patterns=patterns,
        )

        # Step 5: Format similar cases for API response
        formatted_cases = []
        for c in similar_cases:
            formatted_cases.append({
                "case_id": c.get("case_id", ""),
                "case_name": c.get("case_name", ""),
                "court": c.get("court", ""),
                "year": c.get("year", ""),
                "legal_area": c.get("legal_area", ""),
                "case_result": c.get("case_result", ""),
                "similarity_score": c.get("similarity_score", 0),
                "case_summary": c.get("case_summary", ""),
                "judgement_summary": c.get("judgement_summary", ""),
                "case_laws": c.get("case_laws", ""),
                "keywords": c.get("keywords", ""),
                "court_weight": c.get("court_weight", 0.4),
            })

        return {
            "similar_cases": formatted_cases,
            "outcome_predictions": prediction_result,
            "patterns": patterns,
            "reasoning": reasoning_text,
            "confidence_score": prediction_result.get("confidence_score", 0.0),
            "top_outcome": prediction_result.get("top_outcome", "Unknown"),
            "total_cases_in_db": collection_count(),
            "error": None,
        }
