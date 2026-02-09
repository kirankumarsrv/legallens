"""
Workflow 4: Draft Generation Only
- Use all context (facts, arguments, analysis, prediction)
- LLM generates final draft document
"""

from langgraph.graph import StateGraph, END
from workflows.lawyer_agent.state import LawyerState
from workflows.lawyer_agent.nodes.draft_generation import draft_generation_node


def create_draft_generation_workflow(llm):
    """
    Workflow 4: ONLY draft generation.
    Requires facts, arguments, and optionally prediction.
    Uses all available context to generate final draft.
    """
    
    workflow = StateGraph(LawyerState)
    
    # Add node
    workflow.add_node(
        "draft_generation",
        lambda state: draft_generation_node(
            state=state,
            llm=llm
        )
    )
    
    # Define flow
    workflow.set_entry_point("draft_generation")
    workflow.add_edge("draft_generation", END)
    
    return workflow.compile()


def run_draft_generation_workflow(
    state: dict,
    llm
) -> dict:
    """
    Execute Workflow 4: Draft Generation
    Requires state to have facts, arguments, and analysis
    Prediction is optional
    Returns state with draft populated
    """
    
    # Validate required context
    if not state.get("fact_storage"):
        raise ValueError("No facts found. Cannot generate draft without facts.")
    
    if not state.get("argument_storage"):
        raise ValueError("No arguments found. Cannot generate draft without arguments.")
    
    workflow = create_draft_generation_workflow(llm=llm)
    
    result = workflow.invoke(state)
    return result
