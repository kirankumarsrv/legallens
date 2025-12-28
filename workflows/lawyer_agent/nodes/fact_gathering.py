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
    print("   (Statutory sources only)")
    print("   (Constitution, IPC, CrPC)\n")
    
    # Retrieve statutes
    facts = retrieve_statutes(
        query=state["question"],
        chroma_stores=chroma_stores,
        embedding_model=embedding_model,
        k=6
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
