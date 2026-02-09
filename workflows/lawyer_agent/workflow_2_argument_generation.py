"""
Workflow 2: Argument Generation Only
- Use locked facts
- LLM generates arguments
- NO prediction, NO draft
"""

from langgraph.graph import StateGraph, END
from workflows.lawyer_agent.state import LawyerState
from workflows.lawyer_agent.nodes.legal_analysis import legal_analysis_node


def create_argument_generation_workflow(
    llm,
    embedding_model,
    chroma_stores: dict,
    faiss_store=None
):
    """
    Workflow 2: ONLY argument generation from locked facts.
    Requires facts to be locked first.
    """
    
    workflow = StateGraph(LawyerState)
    
    # Add node
    workflow.add_node(
        "legal_analysis",
        lambda state: legal_analysis_node(
            state=state,
            llm=llm,
            embedding_model=embedding_model,
            chroma_stores=chroma_stores,
            faiss_store=faiss_store
        )
    )
    
    # Define flow
    workflow.set_entry_point("legal_analysis")
    workflow.add_edge("legal_analysis", END)
    
    return workflow.compile()


def run_argument_generation_workflow(
    state: dict,
    llm,
    embedding_model,
    chroma_stores: dict,
    faiss_store=None
) -> dict:
    """
    Execute Workflow 2: Argument Generation
    Requires state["facts"] to be populated with locked facts
    Returns state with arguments populated
    """
    
    # Validate locked facts exist
    if not state.get("fact_storage"):
        raise ValueError("No fact_storage found. Cannot generate arguments without facts.")
    
    locked_facts = state["fact_storage"].get_locked_facts()
    if not locked_facts:
        raise ValueError("No locked facts found. Please approve and lock facts first.")
    
    # Set facts in state for analysis
    state["facts"] = locked_facts
    state["facts_approved_and_locked"] = True
    
    workflow = create_argument_generation_workflow(
        llm=llm,
        embedding_model=embedding_model,
        chroma_stores=chroma_stores,
        faiss_store=faiss_store
    )
    
    result = workflow.invoke(state)
    return result
