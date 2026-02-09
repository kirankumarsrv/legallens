"""
Lawyer Agent State Schema

Single source of truth for the entire agent workflow.
Every state modification is traceable and auditable.

This design ensures:
- Type safety
- LangSmith compatibility
- Complete transparency
- Session persistence
- Fact persistence & approval tracking
"""

from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from modules.fact_storage import FactStorage


class LawyerState(TypedDict):
    """
    Complete state schema for lawyer agent workflow.
    
    Attributes:
        question: User's legal question
        
        evidence_files: Paths to uploaded case files (PDFs, FIRs, etc.)
        evidence_text: Parsed text from evidence files (session-scoped)
        
        facts: Retrieved statutory facts (Phase 1)
        facts_raw: Raw document objects
        
        analysis: Legal reasoning and arguments (Phase 2)
        statutes: Retrieved statute sections
        precedents: Retrieved case law
        
        prediction: Outcome prediction (Phase 3)
        similar_cases: Cases used for prediction
        
        draft: Final legal document (Phase 4)
        templates: Document templates used
        citations: Cases cited in draft
        
        approved_phase: Last phase approved by human
        user_feedback: Feedback from human reviewer
        reasoning_trace: Complete reasoning chain for audit
    """
    
    # Input
    question: str
    
    # Evidence Ingestion (NEW)
    evidence_files: Optional[List[str]]
    evidence_text: Optional[str]
    # Detected language of evidence (e.g., "hi", "ta", "en")
    detected_language: Optional[str]
    # Human-readable language name (e.g., "Hindi", "Tamil", "English")
    source_language_name: Optional[str]
    # Extracted entities from evidence (persons, dates, sections, firs...)
    entities: Optional[Dict[str, Any]]
    # Normalized entities (deduplicated, fuzzy-matched)
    normalized_entities: Optional[Dict[str, Any]]
    # Entity conflicts detected (same person in multiple roles)
    entity_conflicts: Optional[List[Dict[str, Any]]]
    # Clarification questions for lawyer (ambiguous entities)
    entity_clarifications: Optional[List[Dict[str, Any]]]
    # Human-readable entity summary (markdown)
    entity_summary: Optional[str]
    # Canonical mapping for entity names (original -> canonical)
    entity_canonical_map: Optional[Dict[str, str]]
    # Timeline constructed from dates and entities
    timeline: Optional[List[Dict[str, Any]]]
    # Cross-evidence contradictions (list of issues for human review)
    contradictions: Optional[List[Dict[str, Any]]]
    
    # Phase 1: Fact Gathering
    facts: Optional[List[Dict[str, Any]]]
    facts_raw: Optional[List[Any]]
    fact_storage: Optional[FactStorage]  # NEW: Manages fact approval status & persistence
    facts_approved_and_locked: Optional[bool]  # NEW: Prevents re-retrieval after approval
    
    # Phase 2: Legal Analysis
    analysis: Optional[str]
    statutes: Optional[List[Dict[str, Any]]]
    precedents: Optional[List[Dict[str, Any]]]
    
    # Phase 3: Prediction
    prediction: Optional[str]
    similar_cases: Optional[List[Dict[str, Any]]]
    prediction_confidence: Optional[float]
    
    # Phase 4: Drafting
    draft: Optional[str]
    templates: Optional[List[Dict[str, Any]]]
    citations: Optional[List[Dict[str, Any]]]
    
    # Human Review
    approved_phase: Optional[str]
    user_feedback: Optional[str]
    
    # Audit Trail
    reasoning_trace: Optional[List[str]]
