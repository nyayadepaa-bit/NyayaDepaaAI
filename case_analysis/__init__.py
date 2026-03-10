"""
case_analysis/
--------------
AI-powered Legal Case Analysis and Prediction System.
Analyzes user cases, retrieves similar precedents, and predicts outcomes.

Modules:
    - analyzer.py           : ChromaDB-based case pipeline
    - pinecone_predictor.py : Pinecone-based prediction engine (multi-condition, duration, strategy)
    - predictor.py          : Outcome prediction with court-weighted frequency
    - reasoning.py          : Pattern analysis and legal reasoning text builder
    - retriever.py          : Semantic similarity retrieval
    - case_embedder.py      : Embedding generation for cases
    - case_store.py         : ChromaDB persistent store
"""
