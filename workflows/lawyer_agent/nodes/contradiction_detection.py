"""
Cross-evidence contradiction detection node

Runs after timeline construction and populates `state['contradictions']`.
"""
from pathlib import Path
from typing import List
from workflows.lawyer_agent.evidence.contradiction_detector import detect_contradictions
from workflows.lawyer_agent.state import LawyerState


def contradiction_detection_node(state: LawyerState) -> LawyerState:
    print("\n⚠️ PHASE: Cross-Evidence Contradiction Detection")

    paths: List[str] = state.get("evidence_files") or []
    if not paths:
        print("   ℹ️  No evidence files provided; skipping contradiction detection.")
        state["contradictions"] = []
        return state

    path_objs = [Path(p) for p in paths]
    contradictions = detect_contradictions(path_objs)
    state["contradictions"] = contradictions

    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    state["reasoning_trace"].append(f"CONTRADICTIONS_DETECTED: {len(contradictions)}")

    if contradictions:
        print(f"   ⚠️ Found {len(contradictions)} potential contradictions (see state['contradictions'])")
    else:
        print("   ✅ No contradictions found across provided evidence files.")

    return state
