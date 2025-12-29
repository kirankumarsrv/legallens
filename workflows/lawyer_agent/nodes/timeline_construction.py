"""
Timeline Construction Node

Builds chronological timeline from extracted entities and evidence text.
Runs after entity/role extraction and before fact gathering.
"""

from workflows.lawyer_agent.evidence.timeline_builder import build_timeline
from workflows.lawyer_agent.state import LawyerState


def timeline_construction_node(state: LawyerState) -> LawyerState:
    """Build timeline from entities and evidence_text.

    Input: state['entities'] and state['evidence_text']
    Output: state['timeline'] - ordered events with associated persons, locations, sections
    """

    print("\n📅 TIMELINE CONSTRUCTION")

    if not state.get("entities") or not state.get("evidence_text"):
        print("   ℹ️  Missing entities or evidence; skipping timeline construction.")
        state["timeline"] = []
        return state

    # Build timeline
    timeline = build_timeline(state["entities"], state["evidence_text"])

    state["timeline"] = timeline

    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []

    state["reasoning_trace"].append(f"TIMELINE: constructed {len(timeline)} events")

    if timeline:
        print(f"   ✅ Constructed timeline with {len(timeline)} events:")
        for event in timeline[:3]:  # Show first 3
            print(f"      • {event['date']}: {event['event'][:60]}...")
        if len(timeline) > 3:
            print(f"      ... and {len(timeline) - 3} more events")
    else:
        print("   ℹ️  No dates found in evidence; empty timeline.")

    return state
