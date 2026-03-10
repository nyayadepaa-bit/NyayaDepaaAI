"""
retrieval/compressor.py
------------------------
Context compression before LLM call.

Reduces retrieved context size by:
    - Removing redundant/overlapping content
    - Extracting key legal sentences
    - Fitting within token budget
"""

import re
import logging

logger = logging.getLogger(__name__)


def _extract_legal_sentences(text: str) -> list[str]:
    """Extract sentences with legal significance."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    legal_indicators = [
        r"section\s*\d+", r"article\s*\d+", r"act[,\s]", r"clause",
        r"rights?", r"shall\b", r"offence", r"punish", r"penalty",
        r"complaint", r"court", r"tribunal", r"FIR", r"bail",
        r"victim", r"protection\s*order", r"maintenance",
        r"compensation", r"damages", r"imprisonment",
        r"harassment", r"violence", r"abuse",
    ]

    scored = []
    for s in sentences:
        s = s.strip()
        if len(s) < 20:
            continue
        score = sum(1 for p in legal_indicators if re.search(p, s, re.IGNORECASE))
        scored.append((score, s))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [s for _, s in scored]


def _deduplicate(sentences: list[str], threshold: float = 0.7) -> list[str]:
    """Remove near-duplicate sentences using simple word overlap."""
    unique = []
    for sent in sentences:
        words = set(sent.lower().split())
        is_dup = False
        for existing in unique:
            existing_words = set(existing.lower().split())
            if not words or not existing_words:
                continue
            overlap = len(words & existing_words) / max(len(words), len(existing_words))
            if overlap > threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(sent)
    return unique


def compress_context(results: list[dict], max_chars: int = 3500) -> str:
    """
    Compress retrieved results into an optimized context string.

    Args:
        results: List of retrieval results with 'text', 'source', 'page', etc.
        max_chars: Max characters for the compressed context

    Returns:
        Compressed context string
    """
    if not results:
        return "No relevant documents found in the legal database."

    # Collect all legal sentences from results
    all_sentences = []
    source_map = {}  # sentence → source info

    for r in results:
        sentences = _extract_legal_sentences(r["text"])
        for s in sentences:
            all_sentences.append(s)
            source_map[s] = {
                "source": r.get("source", "Unknown"),
                "page": r.get("page", 0),
                "act_name": r.get("act_name", ""),
            }

    # Deduplicate
    unique_sentences = _deduplicate(all_sentences)

    # Build compressed context within budget
    parts = []
    char_count = 0
    sources_used = set()

    for sent in unique_sentences:
        info = source_map.get(sent, {})
        source_tag = f"[{info.get('source', 'Unknown')}"
        if info.get("act_name"):
            source_tag += f" — {info['act_name']}"
        source_tag += "]"

        entry = f"{source_tag} {sent}"

        if char_count + len(entry) > max_chars:
            break

        parts.append(entry)
        char_count += len(entry)
        sources_used.add(info.get("source", ""))

    context = "\n\n".join(parts)

    logger.info(
        f"Compressed context: {len(all_sentences)} sentences → "
        f"{len(parts)} selected ({char_count} chars) from {len(sources_used)} sources"
    )

    return context
