"""
Entity extraction node for the Lawyer Agent workflow.

Extracts structured entities from `state['evidence_text']` and stores
them in `state['entities']`.
"""
from workflows.lawyer_agent.evidence.entity_extractor import extract_entities
from workflows.lawyer_agent.state import LawyerState


def entity_extraction_node(state: LawyerState) -> LawyerState:
    """Populate `state['entities']` from evidence_text.

    If no evidence_text is present, set entities to {}.
    """
    print("\n🔎 PHASE: Entity Extraction")
    if not state.get("evidence_text"):
        print("   ℹ️  No evidence text available; skipping entity extraction.")
        state["entities"] = {}
        return state

    entities = extract_entities(state["evidence_text"])
    state["entities"] = entities

    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []

    state["reasoning_trace"].append(f"ENTITY EXTRACTION: found {sum(len(v) for v in entities.values())} entities")
    print(f"   ✅ Extracted entities: {', '.join(entities.keys())}")

    return state
