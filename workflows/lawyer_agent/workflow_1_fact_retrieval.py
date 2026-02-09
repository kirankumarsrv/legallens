"""
Workflow 1: Entity Extraction & Anomaly Detection ONLY
- Extract entities from evidence (LLM-based NER)
- Normalize entities (LLM-based anomaly detection)
- Generate clarification questions for lawyer
- **STOPS HERE** - does NOT proceed to fact gathering
- Returns entity results to UI for lawyer review

Workflow 2 (Fact Gathering) will run AFTER lawyer answers clarifications.
"""

from langgraph.graph import StateGraph, END
from workflows.lawyer_agent.state import LawyerState
from workflows.lawyer_agent.nodes.evidence_ingest import evidence_ingest_node
from workflows.lawyer_agent.nodes.entity_extraction import entity_extraction_node
from workflows.lawyer_agent.nodes.entity_normalization import entity_normalization_node
from workflows.lawyer_agent.nodes.fact_gathering import fact_gathering_node


def create_entity_extraction_workflow(
    llm=None,
    auto_resolve_conflicts: bool = False,
    similarity_threshold: float = 0.85
):
    """
    Workflow 1: Entity extraction and anomaly detection ONLY.
    
    Flow:
    1. Evidence Ingest (load files, detect language)
    2. Entity Extraction (LLM-based NER - persons, dates, sections, etc.)
    3. Entity Normalization (LLM-based anomaly detection)
    4. **END** - Return results to UI, wait for lawyer clarifications
    
    Returns entities, anomalies, and clarification questions.
    Does NOT proceed to fact gathering.
    """
    
    workflow = StateGraph(LawyerState)
    
    # Add nodes for entity extraction only
    workflow.add_node("evidence_ingest", evidence_ingest_node)
    workflow.add_node(
        "entity_extraction",
        lambda state: entity_extraction_node(state=state, llm=llm)
    )
    workflow.add_node(
        "entity_normalization",
        lambda state: entity_normalization_node(
            state=state,
            llm=llm,
            auto_resolve=auto_resolve_conflicts,
            similarity_threshold=similarity_threshold
        )
    )
    
    # Define flow - LINEAR, ends after entity normalization
    workflow.set_entry_point("evidence_ingest")
    workflow.add_edge("evidence_ingest", "entity_extraction")
    workflow.add_edge("entity_extraction", "entity_normalization")
    workflow.add_edge("entity_normalization", END)  # STOP HERE
    
    return workflow.compile()


def create_fact_gathering_workflow(
    chroma_stores: dict,
    embedding_model,
    faiss_store=None,
    llm=None,
    enable_web_search: bool = False,
    enable_research_papers: bool = False,
    enable_google_scholar: bool = True,
    enable_arxiv: bool = True,
    enable_indian_legal_db: bool = True,
    pdf_directory: str = None
):
    """
    Workflow 2: Fact Retrieval with verified entities.
    
    Prerequisites:
    - Workflow 1 must have completed
    - Lawyer must have answered clarification questions
    - Entities must be cleaned and verified
    
    Flow:
    1. Fact Gathering (retrieve from multiple sources using clean entities)
    2. END
    
    Returns facts retrieved from RAG.
    """
    
    workflow = StateGraph(LawyerState)
    
    # Only fact gathering - entities already extracted and verified
    workflow.add_node(
        "fact_gathering",
        lambda state: fact_gathering_node(
            state=state,
            chroma_stores=chroma_stores,
            embedding_model=embedding_model,
            faiss_store=faiss_store,
            llm=llm,
            enable_web_search=enable_web_search,
            enable_research_papers=enable_research_papers,
            enable_google_scholar=enable_google_scholar,
            enable_arxiv=enable_arxiv,
            enable_indian_legal_db=enable_indian_legal_db,
            pdf_directory=pdf_directory
        )
    )
    
    # Simple linear flow
    workflow.set_entry_point("fact_gathering")
    workflow.add_edge("fact_gathering", END)
    
    return workflow.compile()


# Legacy function for backward compatibility
def create_fact_retrieval_workflow(
    chroma_stores: dict,
    embedding_model,
    faiss_store=None,
    llm=None,
    enable_web_search: bool = False,
    enable_research_papers: bool = False,
    enable_google_scholar: bool = True,
    enable_arxiv: bool = True,
    enable_indian_legal_db: bool = True,
    pdf_directory: str = None,
    enable_entity_extraction: bool = True,
    enable_entity_normalization: bool = True,
    auto_resolve_conflicts: bool = False,
    similarity_threshold: float = 0.85
):
    """
    OLD COMBINED WORKFLOW (DEPRECATED)
    Use create_entity_extraction_workflow() and create_fact_retrieval_workflow() separately.
    
    This is kept for backward compatibility only.
    """
    
    workflow = StateGraph(LawyerState)
    
    # Add nodes
    workflow.add_node("evidence_ingest", evidence_ingest_node)
    
    if enable_entity_extraction:
        workflow.add_node(
            "entity_extraction",
            lambda state: entity_extraction_node(state=state, llm=llm)
        )
    
    if enable_entity_normalization:
        workflow.add_node(
            "entity_normalization",
            lambda state: entity_normalization_node(
                state=state,
                llm=llm,
                auto_resolve=auto_resolve_conflicts,
                similarity_threshold=similarity_threshold
            )
        )
    
    workflow.add_node(
        "fact_gathering",
        lambda state: fact_gathering_node(
            state=state,
            chroma_stores=chroma_stores,
            embedding_model=embedding_model,
            faiss_store=faiss_store,
            llm=llm,
            enable_web_search=enable_web_search,
            enable_research_papers=enable_research_papers,
            enable_google_scholar=enable_google_scholar,
            enable_arxiv=enable_arxiv,
            enable_indian_legal_db=enable_indian_legal_db,
            pdf_directory=pdf_directory
        )
    )
    
    # Define flow
    workflow.set_entry_point("evidence_ingest")
    
    if enable_entity_extraction:
        workflow.add_edge("evidence_ingest", "entity_extraction")
        
        if enable_entity_normalization:
            workflow.add_edge("entity_extraction", "entity_normalization")
            workflow.add_edge("entity_normalization", "fact_gathering")
        else:
            workflow.add_edge("entity_extraction", "fact_gathering")
    else:
        workflow.add_edge("evidence_ingest", "fact_gathering")
    
    workflow.add_edge("fact_gathering", END)
    
    return workflow.compile()


def run_fact_retrieval_workflow(
    state: dict,
    chroma_stores: dict,
    embedding_model,
    faiss_store=None,
    llm=None,
    enable_web_search: bool = False,
    enable_research_papers: bool = False,
    enable_google_scholar: bool = True,
    enable_arxiv: bool = True,
    enable_indian_legal_db: bool = True,
    pdf_directory: str = None,
    enable_entity_extraction: bool = True,
    enable_entity_normalization: bool = True,
    auto_resolve_conflicts: bool = False,
    similarity_threshold: float = 0.85
) -> dict:
    """
    Execute Workflow 1: Fact Retrieval with Entity Processing
    
    Args:
        enable_entity_extraction: Enable NER (persons, dates, sections, etc.)
        enable_entity_normalization: Enable fuzzy matching & deduplication
        auto_resolve_conflicts: Use LLM to auto-resolve high-confidence conflicts
        similarity_threshold: Fuzzy matching threshold (0.85 = 85% similar)
    
    Returns state with facts and normalized entities populated
    """
    workflow = create_fact_retrieval_workflow(
        chroma_stores=chroma_stores,
        embedding_model=embedding_model,
        faiss_store=faiss_store,
        llm=llm,
        enable_web_search=enable_web_search,
        enable_research_papers=enable_research_papers,
        enable_google_scholar=enable_google_scholar,
        enable_arxiv=enable_arxiv,
        enable_indian_legal_db=enable_indian_legal_db,
        pdf_directory=pdf_directory,
        enable_entity_extraction=enable_entity_extraction,
        enable_entity_normalization=enable_entity_normalization,
        auto_resolve_conflicts=auto_resolve_conflicts,
        similarity_threshold=similarity_threshold
    )
    
    result = workflow.invoke(state)
    return result
