"""
Workflow 3: Prediction Only
- Use existing arguments (NO retrieval)
- LLM generates prediction based on arguments
- NO draft
"""

from langgraph.graph import StateGraph, END
from workflows.lawyer_agent.state import LawyerState
from workflows.lawyer_agent.nodes.prediction import prediction_node


def create_prediction_workflow(llm, embedding_model, faiss_store=None):
    """
    Workflow 3: ONLY prediction generation based on existing arguments.
    Requires arguments to be generated first (Workflow 2).
    NO retrieval is performed.
    """
    
    workflow = StateGraph(LawyerState)
    
    # Add node
    workflow.add_node(
        "prediction",
        lambda state: prediction_node(
            state=state,
            llm=llm,
            embedding_model=embedding_model,
            faiss_store=faiss_store
        )
    )
    
    # Define flow
    workflow.set_entry_point("prediction")
    workflow.add_edge("prediction", END)
    
    return workflow.compile()


def run_prediction_workflow(
    state: dict,
    llm,
    embedding_model,
    faiss_store=None
) -> dict:
    """
    Execute Workflow 3: Prediction
    Requires state["argument_storage"] to be populated with arguments
    Returns state with prediction populated
    """
    
    # Validate arguments exist
    if not state.get("argument_storage"):
        raise ValueError("No argument_storage found. Cannot generate prediction without arguments.")
    
    arguments = state["argument_storage"].get_all_arguments()
    if not arguments:
        raise ValueError("No arguments found. Please generate arguments first (Workflow 2).")
    
    workflow = create_prediction_workflow(
        llm=llm,
        embedding_model=embedding_model,
        faiss_store=faiss_store
    )
    
    result = workflow.invoke(state)
    return result
