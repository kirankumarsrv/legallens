"""
Evidence Ingestion Node

Entry point for the lawyer agent workflow.
Loads and parses user-uploaded case files before legal reasoning.

This is the FIRST phase: ingest private evidence into session state.
"""

from workflows.lawyer_agent.evidence.loader import load_evidence_files
from workflows.lawyer_agent.evidence.parser import parse_evidence
from workflows.lawyer_agent.nodes.language_detection import (
    detect_language_with_confidence,
    LANGUAGE_NAMES,
)
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
    
    # Detect language of evidence
    print("🌐 Detecting language...")
    lang_result = detect_language_with_confidence(evidence_text)
    detected_lang = lang_result.get("primary_language")
    lang_name = lang_result.get("primary_language_name", "Unknown")
    confidence = lang_result.get("confidence", 0)
    
    state["detected_language"] = detected_lang
    state["source_language_name"] = lang_name
    
    if detected_lang:
        print(f"   ✅ Language detected: {lang_name} ({detected_lang}) - {confidence:.0%} confidence")
        if confidence < 0.7:
            print(f"   ⚠️  Low confidence ({confidence:.0%}). Results may be inaccurate.")
    else:
        print(f"   ⚠️  Language detection failed. Defaulting to English.")
        state["detected_language"] = "en"
        state["source_language_name"] = "English"
    
    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    
    state["reasoning_trace"].append(
        f"PHASE 0: Loaded and parsed {len(files)} evidence file(s). Total: {len(evidence_text)} chars. "
        f"Language: {lang_name} ({detected_lang}, {confidence:.0%} confidence)"
    )
    
    print(f"   ✅ Evidence loaded and language detected\n")
    
    return state
