"""
Role Classification Node

Classifies extracted person entities into legal roles.

This node runs AFTER entity extraction and enriches persons with role info.
"""

from workflows.lawyer_agent.evidence.role_classifier import classify_roles
from workflows.lawyer_agent.state import LawyerState


def role_classification_node(state: LawyerState, llm_manager=None) -> LawyerState:
    """Classify roles for extracted persons.

    Input: state['entities'] with persons list
    Output: Updated state['entities'] with role field on each person

    If no entities or no persons, pass through unchanged.
    """

    print("\n👥 ROLE CLASSIFICATION")

    if not state.get("entities") or not state["entities"].get("persons"):
        print("   ℹ️  No persons extracted; skipping role classification.")
        return state

    evidence_text = state.get("evidence_text", "")
    if not evidence_text:
        print("   ⚠️  No evidence text available for context.")
        return state

    # Classify roles
    entities = classify_roles(
        entities=state["entities"],
        evidence_text=evidence_text,
        llm_manager=llm_manager,
    )

    state["entities"] = entities

    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []

    # Count roles
    role_counts = {}
    for person in entities.get("persons", []):
        role = person.get("role", "other")
        role_counts[role] = role_counts.get(role, 0) + 1

    role_summary = ", ".join([f"{role}({count})" for role, count in sorted(role_counts.items())])
    state["reasoning_trace"].append(f"ROLE CLASSIFICATION: {role_summary}")

    print(f"   ✅ Classified {len(entities.get('persons', []))} persons: {role_summary}")

    return state
