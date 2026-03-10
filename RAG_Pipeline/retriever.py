"""
RAG_Pipeline/retriever.py
--------------------------
Retrieves relevant legal document chunks from Pinecone given a query.
Supports optional reranking with cross-encoder for higher precision.

Usage (standalone):
    from retriever import LegalRetriever
    retriever = LegalRetriever()
    results = retriever.retrieve("What are the grounds for bail under CrPC?")
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer, CrossEncoder

load_dotenv()
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
RERANK_MODEL    = "cross-encoder/ms-marco-MiniLM-L-6-v2"   # optional reranker
TOP_K_RETRIEVE  = 10    # initial candidates from Pinecone
TOP_K_RERANK    = 5     # final results after reranking
USE_RERANKER    = True
# ============================================================

PINECONE_API_KEY    = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "legal-llama-index")


class LegalRetriever:
    def __init__(
        self,
        top_k_retrieve: int = TOP_K_RETRIEVE,
        top_k_rerank: int = TOP_K_RERANK,
        use_reranker: bool = USE_RERANKER,
    ):
        self.top_k_retrieve = top_k_retrieve
        self.top_k_rerank   = top_k_rerank
        self.use_reranker   = use_reranker

        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY not set. ### ADD IT TO .env ###")

        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

        logger.info("Connecting to Pinecone...")
        pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index = pc.Index(PINECONE_INDEX_NAME)

        if use_reranker:
            logger.info(f"Loading reranker: {RERANK_MODEL}")
            self.reranker = CrossEncoder(RERANK_MODEL)

    def retrieve(
        self,
        query: str,
        source_filter: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a given query.

        Args:
            query:         Natural language legal query
            source_filter: Optionally filter by PDF filename
            top_k:         Override default top_k

        Returns:
            List of dicts with keys: text, source, page, score
        """
        k = top_k or self.top_k_retrieve

        # Embed the query
        query_embedding = self.embedder.encode(
            query, normalize_embeddings=True
        ).tolist()

        # Build filter if needed
        filter_dict = None
        if source_filter:
            filter_dict = {"source": {"$eq": source_filter}}

        # Query Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True,
            filter=filter_dict,
        )

        candidates = [
            {
                "text": match.metadata.get("text", ""),
                "source": match.metadata.get("source", ""),
                "page": match.metadata.get("page", -1),
                "score": match.score,
                "id": match.id,
            }
            for match in results.matches
        ]

        # Optional reranking
        if self.use_reranker and len(candidates) > 1:
            candidates = self._rerank(query, candidates)

        return candidates[:self.top_k_rerank]

    def _rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        """Rerank candidates using cross-encoder for higher precision."""
        pairs = [(query, c["text"]) for c in candidates]
        scores = self.reranker.predict(pairs)

        for c, s in zip(candidates, scores):
            c["rerank_score"] = float(s)

        return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

    def format_context(self, results: list[dict], max_chars: int = 3000) -> str:
        """Format retrieved chunks into a single context string for the LLM."""
        context_parts = []
        total_chars = 0

        for i, r in enumerate(results):
            chunk = f"[Source: {r['source']}, Page {r['page']}]\n{r['text']}"
            if total_chars + len(chunk) > max_chars:
                break
            context_parts.append(chunk)
            total_chars += len(chunk)

        return "\n\n---\n\n".join(context_parts)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What are the grounds for bail?"
    retriever = LegalRetriever()
    results = retriever.retrieve(query)
    print(f"\nTop {len(results)} results for: '{query}'\n")
    for i, r in enumerate(results):
        print(f"{i+1}. [{r['source']} p.{r['page']}] score={r['score']:.3f}")
        print(f"   {r['text'][:200]}...\n")
