"""
Phase 1: Fact Gathering Node

Retrieves statutory facts only.
NO case law, NO interpretation at this stage.

Like reading the FIR before going to court.
"""

from workflows.lawyer_agent.retrieval.statutes import retrieve_statutes
from workflows.lawyer_agent.state import LawyerState


def fact_gathering_node(state: LawyerState, chroma_stores: dict, embedding_model) -> LawyerState:
    """
    First phase: Gather statutory material.
    
    Inputs from state:
        - question: User's legal question
    
    Outputs to state:
        - facts: Retrieved statutory documents
        - facts_raw: Raw document objects
        - reasoning_trace: Audit trail
    
    Philosophy:
        ✔ Facts only (no opinions)
        ✔ Statutes only (no cases)
        ✔ Pure retrieval (no logic)
    """
    
    print("\n📋 PHASE 1: FACT GATHERING")
    print("   Objectives:")
    print("   - Extract key entities (parties, dates, legal issues)")
    print("   - Retrieve applicable statutes (Constitution, IPC, CrPC)")
    print("   - Establish factual timeline")
    print("   - Do NOT analyze yet; just gather facts & applicable law\n")
    
    # Extract target years if provided (from revise_action)
    target_years = None
    if state.get("revise_action") and state["revise_action"].get("constraint_years"):
        target_years = state["revise_action"]["constraint_years"]
        print(f"   🎯 Using revised year constraints: {target_years}\n")
    
    # Retrieve statutes
    facts = retrieve_statutes(
        query=state["question"],
        chroma_stores=chroma_stores,
        embedding_model=embedding_model,
        k=6,
        target_years=target_years
    )
    
    # Update state
    state["facts"] = facts
    state["facts_raw"] = [f.get("content") for f in facts]
    
    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    
    state["reasoning_trace"].append(
        f"PHASE 1: Retrieved {len(facts)} statute sections"
    )
    
    return state
