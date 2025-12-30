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
from workflows.lawyer_agent.nodes.contradiction_detection import contradiction_detection_node
from workflows.lawyer_agent.nodes.fact_gathering import fact_gathering_node
from workflows.lawyer_agent.nodes.interactive_fact_refiner import (
    retrieve_facts_node,
    fact_display_node,
    per_fact_chat_node,
    fact_approval_node,
)
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
    
    # Phase 1: Fact Retrieval + Interactive Refinement
    def retrieve_facts_wrapper(state: LawyerState) -> LawyerState:
        import os
        enable_web_search = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
        enable_research_papers = os.getenv("ENABLE_RESEARCH_PAPERS", "true").lower() == "true"
        pdf_directory = os.getenv("PDF_RESEARCH_DIRECTORY", "./research_papers")

        return retrieve_facts_node(
            state,
            dependencies["chroma_stores"],
            dependencies["embedding_model"],
            enable_web_search=enable_web_search,
            enable_research_papers=enable_research_papers,
            pdf_directory=pdf_directory,
        )

    graph.add_node("retrieve_facts", retrieve_facts_wrapper)

    # Display + per-fact interactive nodes
    graph.add_node("fact_display", fact_display_node)
    graph.add_node("per_fact_chat", per_fact_chat_node)

    # Phase 1.1: Entity Extraction (from evidence)
    graph.add_node("entities", entity_extraction_node)

    # Phase 1.2: Role Classification (enrich persons with roles)
    def role_classification_wrapper(state: LawyerState) -> LawyerState:
        return role_classification_node(state, llm_manager=dependencies.get("llm"))
    
    graph.add_node("roles", role_classification_wrapper)

    # Phase 1.3: Timeline Construction (order events chronologically)
    graph.add_node("timeline", timeline_construction_node)

    # Phase 1.4: Cross-evidence Contradiction Detection
    graph.add_node("contradictions", contradiction_detection_node)
    
    # Gate 1: Approve facts
    def approve_facts(state: LawyerState) -> LawyerState:
        # First run the generic human approval gate (UI/CLI). After that, lock approved facts.
        state = human_approval_node(state, "facts", llm=dependencies.get("llm"), embedding_model=dependencies.get("embedding_model"))
        return fact_approval_node(state, llm=dependencies.get("llm"), embedding_model=dependencies.get("embedding_model"))

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
    graph.add_edge("timeline", "contradictions")
    graph.add_edge("contradictions", "retrieve_facts")
    graph.add_edge("retrieve_facts", "fact_display")
    graph.add_edge("fact_display", "per_fact_chat")
    graph.add_edge("per_fact_chat", "approve_facts")
    graph.add_edge("approve_facts", "legal_analysis")
    graph.add_edge("legal_analysis", "approve_analysis")
    graph.add_edge("approve_analysis", "prediction")
    graph.add_edge("prediction", "approve_prediction")
    graph.add_edge("approve_prediction", "drafting")
    graph.add_edge("drafting", "approve_draft")
    graph.add_edge("approve_draft", END)
    
    return graph.compile()
