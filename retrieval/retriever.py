"""
retrieval/retriever.py
-----------------------
MMR-based retrieval with namespace routing.

Features:
    - Routes queries to relevant Pinecone namespace(s)
    - Maximal Marginal Relevance for diverse results
    - Hybrid: semantic + keyword matching
    - Falls back to all-namespace search if domain unclear
"""

import logging
import numpy as np
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import PINECONE_API_KEY, PINECONE_INDEX_NAME, TOP_K_RETRIEVE, LEGAL_NAMESPACES
from pipeline.embedder import embed_query, get_pinecone_index

logger = logging.getLogger(__name__)


def mmr_select(
    query_embedding: list[float],
    doc_embeddings: list[list[float]],
    doc_indices: list[int],
    k: int = 5,
    lambda_param: float = 0.7,
) -> list[int]:
    """
    Maximal Marginal Relevance selection for diversity.

    Args:
        query_embedding: Query vector
        doc_embeddings: Document vectors
        doc_indices: Original indices
        k: Number to select
        lambda_param: Balance relevance (1.0) vs diversity (0.0)

    Returns:
        Selected indices
    """
    if not doc_embeddings:
        return []

    q = np.array(query_embedding)
    docs = np.array(doc_embeddings)

    # Cosine similarities to query
    q_norm = q / (np.linalg.norm(q) + 1e-10)
    doc_norms = docs / (np.linalg.norm(docs, axis=1, keepdims=True) + 1e-10)
    sim_to_query = doc_norms @ q_norm

    selected = []
    remaining = list(range(len(docs)))

    for _ in range(min(k, len(docs))):
        if not remaining:
            break

        best_idx = None
        best_score = -float("inf")

        for idx in remaining:
            relevance = sim_to_query[idx]

            # Max similarity to already selected docs
            if selected:
                selected_vecs = doc_norms[selected]
                sim_to_selected = doc_norms[idx] @ selected_vecs.T
                max_sim = np.max(sim_to_selected)
            else:
                max_sim = 0.0

            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)

    return [doc_indices[i] for i in selected]


def retrieve(
    query: str,
    namespaces: Optional[list[str]] = None,
    top_k: int = None,
    use_mmr: bool = True,
) -> list[dict]:
    """
    Retrieve relevant legal document chunks.

    Args:
        query: User query
        namespaces: List of namespaces to search (None = all)
        top_k: Number of results
        use_mmr: Apply MMR diversity selection

    Returns:
        List of result dicts with text, metadata, score
    """
    top_k = top_k or TOP_K_RETRIEVE
    index = get_pinecone_index()
    query_embedding = embed_query(query)

    # Determine namespaces to search
    search_namespaces = namespaces or [""]

    if not namespaces:
        # Always include domestic_violence (PDF cases) + all other namespaces
        search_namespaces = list(dict.fromkeys(["domestic_violence"] + LEGAL_NAMESPACES + [""]))

    all_results = []

    for ns in search_namespaces:
        try:
            response = index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=ns if ns else None,
            )

            for match in response.get("matches", []):
                meta = match.get("metadata", {})
                all_results.append({
                    "id":               match["id"],
                    "score":            float(match["score"]),
                    "text":             meta.get("text", ""),
                    # legacy fields
                    "source":           meta.get("source_file", meta.get("source", "Unknown")),
                    "page":             meta.get("page", 0),
                    "act_name":         meta.get("act_name", ""),
                    "legal_category":   meta.get("legal_area", meta.get("legal_category", ns)),
                    "sections_found":   meta.get("sections_found", ""),
                    "keywords":         meta.get("keywords", ""),
                    # case-specific fields
                    "case_name":        meta.get("case_name", ""),
                    "petitioner":       meta.get("petitioner", ""),
                    "respondent":       meta.get("respondent", ""),
                    "filed_by":         meta.get("filed_by", ""),
                    "filed_against":    meta.get("filed_against", ""),
                    "appeal_number":    meta.get("appeal_number", ""),
                    "court":            meta.get("court", ""),
                    "judge_name":       meta.get("judge_name", ""),
                    "cnr_number":       meta.get("cnr_number", ""),
                    "year":             meta.get("year", ""),
                    "filing_date":      meta.get("filing_date", ""),
                    "decision_date":    meta.get("decision_date", ""),
                    "duration":         meta.get("duration", ""),
                    "case_result":      meta.get("case_result", ""),
                    "case_laws":        meta.get("case_laws", []),
                    "maintenance_rs":   meta.get("maintenance_rs", 0),
                    "judgement_summary": meta.get("judgement_summary", ""),
                    # judge reasoning fields
                    "judge_reasoning":  meta.get("judge_reasoning", ""),
                    "decision_basis":   meta.get("decision_basis", []),
                    "court_observations": meta.get("court_observations", ""),
                    "final_order":      meta.get("final_order", ""),
                    "evidence_types":   meta.get("evidence_types", []),
                    "allegations":      meta.get("allegations", []),
                    "namespace":        ns,
                    "embedding":        match.get("values"),
                })
        except Exception as e:
            logger.warning(f"Query failed for namespace '{ns}': {e}")
            continue

    # Sort by score
    all_results.sort(key=lambda x: x["score"], reverse=True)

    # Cap at top_k * 2 for MMR processing
    candidates = all_results[: top_k * 2]

    if use_mmr and len(candidates) > top_k:
        # Apply MMR for diversity
        embeddings_present = [r for r in candidates if r.get("embedding")]
        if len(embeddings_present) >= top_k:
            doc_embeddings = [r["embedding"] for r in embeddings_present]
            doc_indices = list(range(len(embeddings_present)))

            selected_indices = mmr_select(
                query_embedding, doc_embeddings, doc_indices, k=top_k
            )
            candidates = [embeddings_present[i] for i in selected_indices]
        else:
            candidates = candidates[:top_k]
    else:
        candidates = candidates[:top_k]

    # Remove embedding from results (save memory)
    for r in candidates:
        r.pop("embedding", None)

    # Keyword boost: re-score with keyword overlap
    query_words = set(query.lower().split())
    for r in candidates:
        kw_score = sum(1 for w in query_words if w in r["text"].lower())
        r["keyword_score"] = kw_score
        r["combined_score"] = r["score"] + (kw_score * 0.02)

    candidates.sort(key=lambda x: x["combined_score"], reverse=True)

    logger.info(f"Retrieved {len(candidates)} results from {len(search_namespaces)} namespaces")
    return candidates


def format_context(results: list[dict], max_chars: int = 4000) -> str:
    """Format retrieved chunks into a rich context string for the LLM."""
    if not results:
        return ""

    parts = []
    char_count = 0

    for i, r in enumerate(results):
        # ── Build a rich header that the LLM can reference ──
        case_name = r.get("case_name") or r.get("source", "Unknown")
        header_parts = [f"[Case {i+1}: {case_name}"]

        if r.get("petitioner") and r["petitioner"] not in ("", "Unknown"):
            header_parts.append(f"  Filed by  : {r['petitioner']}")
        if r.get("respondent") and r["respondent"] not in ("", "Unknown"):
            header_parts.append(f"  Against   : {r['respondent']}")
        if r.get("court"):
            header_parts.append(f"  Court     : {r['court']}")
        if r.get("judge_name") and r["judge_name"] not in ("", "Unknown"):
            header_parts.append(f"  Judge     : {r['judge_name']}")
        if r.get("appeal_number") and r["appeal_number"] not in ("", "Unknown"):
            header_parts.append(f"  Appeal    : {r['appeal_number']}")
        if r.get("cnr_number") and r["cnr_number"] not in ("", "Unknown"):
            header_parts.append(f"  CNR       : {r['cnr_number']}")
        if r.get("filing_date") and r["filing_date"] not in ("", "Unknown"):
            header_parts.append(f"  Filed     : {r['filing_date']}")
        if r.get("decision_date") and r["decision_date"] not in ("", "Unknown"):
            header_parts.append(f"  Decided   : {r['decision_date']}")
        if r.get("case_result"):
            header_parts.append(f"  Result    : {r['case_result']}")
        if r.get("maintenance_rs") and r["maintenance_rs"] > 0:
            header_parts.append(f"  Maintenance: Rs.{r['maintenance_rs']}/month")
        laws = r.get("case_laws", [])
        if laws:
            header_parts.append(f"  Laws      : {', '.join(laws) if isinstance(laws, list) else laws}")
        if r.get("act_name"):
            header_parts.append(f"  Act       : {r['act_name']}")
        if r.get("sections_found"):
            header_parts.append(f"  Sections  : {r['sections_found']}")
        header_parts.append("]")

        header = "\n".join(header_parts)
        body   = r.get("judgement_summary") or r.get("text", "")
        entry  = f"{header}\n{body}\n"

        if char_count + len(entry) > max_chars:
            break

        parts.append(entry)
        char_count += len(entry)

    return "\n---\n".join(parts)
