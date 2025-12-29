"""
Evidence Ingestion Node

Entry point for the lawyer agent workflow.
Loads and parses user-uploaded case files before legal reasoning.

This is the FIRST phase: ingest private evidence into session state.
"""

from workflows.lawyer_agent.evidence.loader import load_evidence_files
from workflows.lawyer_agent.evidence.parser import parse_evidence
from workflows.lawyer_agent.state import LawyerState


def evidence_ingest_node(state: LawyerState) -> LawyerState:
    """
    Load and parse user-uploaded case files.
    
    Inputs from state:
        - evidence_files: List of file paths to load
    
    Outputs to state:
        - evidence_text: Parsed text from all files (session-scoped)
    
    Philosophy:
        ✔ Evidence is first-class input (not supplementary)
        ✔ Evidence lives only in session (not global DB)
        ✔ Private case files are kept confidential
        ✔ No external storage or logging of evidence
    """
    
    print("\n📁 EVIDENCE INGESTION")
    print("   (Load user-uploaded case files)")
    print("   (Session-scoped, not persisted)\n")
    
    # If no evidence files provided, skip silently
    if not state.get("evidence_files"):
        print("   ℹ️  No evidence files provided. Proceeding with question alone.\n")
        state["evidence_text"] = None
        return state
    
    # Load files
    files = load_evidence_files(state["evidence_files"])
    if not files:
        print("   ⚠️  No valid evidence files found.\n")
        state["evidence_text"] = None
        return state
    
    # Parse files
    evidence_text = parse_evidence(files)
    state["evidence_text"] = evidence_text
    
    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    
    state["reasoning_trace"].append(
        f"PHASE 0: Loaded and parsed {len(files)} evidence file(s). Total: {len(evidence_text)} chars"
    )
    
    print(f"   ✅ Evidence loaded into session state\n")
    
    return state
