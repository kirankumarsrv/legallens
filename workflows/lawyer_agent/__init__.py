"""
Lawyer Agent - Multi-phase Legal Reasoning System

Enterprise-grade legal AI with:
- Deterministic retrieval
- Human-in-the-loop approval gates
- Court-safe reasoning
- Explainable predictions
- Session-based workflow

Architecture:
    - state.py: Shared state schema (source of truth)
    - nodes/: Each phase is a separate node
    - retrieval/: Pure RAG layer (no logic)
    - graph.py: LangGraph wiring
    - run.py: Entry point
"""
