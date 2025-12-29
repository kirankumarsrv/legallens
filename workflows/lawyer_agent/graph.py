"""
LangGraph for Lawyer Agent

Architecture:
    evidence → facts → approve_facts → analysis → approve_analysis → prediction → approve_prediction → draft → approve_draft

Entry point is EVIDENCE INGESTION (Phase 0) - loads user-uploaded case files.
Each arrow is a conditional edge:
    - approve: Continue
    - revise: Backtrack (not implemented here)
    - stop: Halt

All phases are sequential.
Human approval gate between each phase.
"""

from langgraph.graph import StateGraph, START, END
from workflows.lawyer_agent.state import LawyerState
from workflows.lawyer_agent.nodes.evidence_ingest import evidence_ingest_node
from workflows.lawyer_agent.nodes.entity_extraction import entity_extraction_node
from workflows.lawyer_agent.nodes.role_classification import role_classification_node
from workflows.lawyer_agent.nodes.timeline_construction import timeline_construction_node
from workflows.lawyer_agent.nodes.fact_gathering import fact_gathering_node
from workflows.lawyer_agent.nodes.legal_analysis import legal_analysis_node
from workflows.lawyer_agent.nodes.prediction import prediction_node
from workflows.lawyer_agent.nodes.drafting import drafting_node
from workflows.lawyer_agent.nodes.human_approval import human_approval_node


def build_lawyer_agent_graph(dependencies: dict) -> StateGraph:
    """
    Assemble the complete Lawyer Agent workflow.
    
    Args:
        dependencies: Dict with keys:
            - llm: LLM instance (Groq)
            - chroma_stores: Dict of ChromaVectorStore instances
            - chroma_drafts: ChromaVectorStore for templates
            - faiss_store: FAISSVectorStore for precedents
            - embedding_model: Embeddings instance
    
    Returns:
        Compiled StateGraph ready to invoke
    """
    
    graph = StateGraph(LawyerState)
    
    # Define nodes
    
    # Phase 0: Evidence Ingestion (ENTRY POINT - NEW)
    graph.add_node("evidence", evidence_ingest_node)
    
    # Phase 1: Fact Gathering
    def fact_gathering_wrapper(state: LawyerState) -> LawyerState:
        return fact_gathering_node(
            state,
            dependencies["chroma_stores"],
            dependencies["embedding_model"]
        )
    
    graph.add_node("fact_gathering", fact_gathering_wrapper)

    # Phase 1.1: Entity Extraction (from evidence)
    graph.add_node("entities", entity_extraction_node)

    # Phase 1.2: Role Classification (enrich persons with roles)
    def role_classification_wrapper(state: LawyerState) -> LawyerState:
        return role_classification_node(state, llm_manager=dependencies.get("llm"))
    
    graph.add_node("roles", role_classification_wrapper)

    # Phase 1.3: Timeline Construction (order events chronologically)
    graph.add_node("timeline", timeline_construction_node)
    
    # Gate 1: Approve facts
    def approve_facts(state: LawyerState) -> LawyerState:
        return human_approval_node(state, "facts", llm=dependencies.get("llm"), embedding_model=dependencies.get("embedding_model"))
    
    graph.add_node("approve_facts", approve_facts)
    
    # Phase 2: Legal Analysis
    def legal_analysis_wrapper(state: LawyerState) -> LawyerState:
        return legal_analysis_node(
            state,
            dependencies["chroma_stores"],
            dependencies["embedding_model"],
            dependencies["faiss_store"],
            dependencies["llm"]
        )
    
    graph.add_node("legal_analysis", legal_analysis_wrapper)
    
    # Gate 2: Approve analysis
    def approve_analysis(state: LawyerState) -> LawyerState:
        return human_approval_node(state, "analysis", llm=dependencies.get("llm"), embedding_model=dependencies.get("embedding_model"))
    
    graph.add_node("approve_analysis", approve_analysis)
    
    # Phase 3: Prediction
    def prediction_wrapper(state: LawyerState) -> LawyerState:
        return prediction_node(
            state,
            dependencies["faiss_store"],
            dependencies["llm"],
            dependencies["embedding_model"]
        )
    
    graph.add_node("prediction", prediction_wrapper)
    
    # Gate 3: Approve prediction
    def approve_prediction(state: LawyerState) -> LawyerState:
        return human_approval_node(state, "prediction", llm=dependencies.get("llm"), embedding_model=dependencies.get("embedding_model"))
    
    graph.add_node("approve_prediction", approve_prediction)
    
    # Phase 4: Drafting
    def drafting_wrapper(state: LawyerState) -> LawyerState:
        return drafting_node(
            state,
            dependencies["chroma_drafts"],
            dependencies["embedding_model"],
            dependencies["faiss_store"],
            dependencies["llm"]
        )
    
    graph.add_node("drafting", drafting_wrapper)
    
    # Gate 4: Approve draft
    def approve_draft(state: LawyerState) -> LawyerState:
        return human_approval_node(state, "draft", llm=dependencies.get("llm"), embedding_model=dependencies.get("embedding_model"))
    
    graph.add_node("approve_draft", approve_draft)
    
    # Define edges (always sequential in this version)
    # Entry point: Evidence Ingestion (Phase 0) - LOADS CASE FILES FIRST
    graph.add_edge(START, "evidence")
    graph.add_edge("evidence", "entities")
    graph.add_edge("entities", "roles")
    graph.add_edge("roles", "timeline")
    graph.add_edge("timeline", "fact_gathering")
    graph.add_edge("fact_gathering", "approve_facts")
    graph.add_edge("approve_facts", "legal_analysis")
    graph.add_edge("legal_analysis", "approve_analysis")
    graph.add_edge("approve_analysis", "prediction")
    graph.add_edge("prediction", "approve_prediction")
    graph.add_edge("approve_prediction", "drafting")
    graph.add_edge("drafting", "approve_draft")
    graph.add_edge("approve_draft", END)
    
    return graph.compile()
