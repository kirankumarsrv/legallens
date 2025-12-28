"""
Adaptive RAG Graph Module

Defines the complete Adaptive RAG workflow.

Flow:
    adaptive_decision → 
        NO_RETRIEVAL → answer
        METADATA_ONLY → metadata → answer
        FULL_RAG → metadata → faiss → grade → answer
"""

from typing import TypedDict, List
from langgraph.graph import StateGraph
from langchain_core.documents import Document

from workflows.adaptive_rag.decision import adaptive_decision
from workflows.tool_rag.tools import (
    metadata_lookup_tool,
    yearwise_faiss_retrieval_tool
)


# -------------------------
# STATE SCHEMA
# -------------------------
class AdaptiveRAGState(TypedDict):
    """State schema for Adaptive RAG workflow."""
    question: str

    # adaptive decision
    mode: str  # "NO_RETRIEVAL" | "METADATA_ONLY" | "FULL_RAG"

    # metadata stage
    years: List[int]
    summaries: List[str]

    # retrieval stage
    retrieved_docs: List[Document]
    filtered_docs: List[Document]

    # final
    answer: str


# -------------------------
# NODE 1: ADAPTIVE DECISION
# -------------------------
def adaptive_node(state: AdaptiveRAGState, llm):
    """
    First node: Decide retrieval strategy.
    
    Routes to: answer (NO_RETRIEVAL) or metadata (METADATA_ONLY/FULL_RAG)
    """
    mode = adaptive_decision(state["question"], llm)
    return {"mode": mode}


# -------------------------
# NODE 2: METADATA LOOKUP
# -------------------------
def metadata_node(state: AdaptiveRAGState, metadata_tool, embedding_model):
    """
    Second node: Retrieve metadata.
    
    Used by both METADATA_ONLY and FULL_RAG modes.
    Routes to: answer (METADATA_ONLY) or faiss (FULL_RAG)
    """
    metadata = metadata_tool(state["question"], embedding_model)
    return {
        "years": metadata["years"],
        "summaries": metadata["summaries"]
    }


# -------------------------
# NODE 3: TARGETED FAISS
# -------------------------
def faiss_node(state: AdaptiveRAGState, faiss_tool, embedding_model):
    """
    Third node: Retrieve detailed documents.
    
    Only executes for FULL_RAG mode.
    Routes to: grade
    """
    docs = faiss_tool(
        query=state["question"],
        years=state["years"],
        embedding_model=embedding_model
    )
    return {"retrieved_docs": docs}


# -------------------------
# NODE 4: CORRECTIVE GRADING
# -------------------------
def grading_node(state: AdaptiveRAGState, llm):
    """
    Fourth node: Filter documents based on relevance.
    
    Self-RAG grading to ensure only relevant docs are used.
    Routes to: answer
    """
    # Import here to avoid circular imports
    from workflows.corrective_rag.grader import grade_documents
    
    filtered = grade_documents(
        question=state["question"],
        documents=state["retrieved_docs"],
        llm=llm
    )
    return {"filtered_docs": filtered}


# -------------------------
# NODE 5: ANSWER GENERATION
# -------------------------
def answer_node(state: AdaptiveRAGState, llm):
    """
    Final node: Generate answer based on selected strategy.
    
    Context source depends on mode:
    - NO_RETRIEVAL: No context, use general knowledge
    - METADATA_ONLY: Use metadata summaries
    - FULL_RAG: Use filtered documents from corrective grading
    """

    if state["mode"] == "NO_RETRIEVAL":
        context = ""
        context_source = "general knowledge"
    elif state["mode"] == "METADATA_ONLY":
        context = "\n\n".join(state["summaries"])
        context_source = "metadata summaries"
    else:  # FULL_RAG
        context = "\n\n".join(d.page_content for d in state["filtered_docs"])
        context_source = "filtered legal documents"

    prompt = f"""You are a legal assistant answering based on Indian law.
Answer ONLY using the provided context (if any). Do not add external knowledge.

Context ({context_source}):
{context if context else "No context provided - use general knowledge."}

Question:
{state['question']}

Answer:"""

    answer = llm.generate(prompt)
    return {"answer": answer}


# -------------------------
# BUILD GRAPH
# -------------------------
def build_adaptive_rag_graph(llm, embedding_model):
    """
    Construct the complete Adaptive RAG workflow.
    
    Nodes:
        1. adaptive → routing decision
        2. metadata → retrieve summaries and years
        3. faiss → retrieve detailed documents
        4. grade → corrective grading / filtering
        5. answer → final answer generation
    
    Flow:
        adaptive → {
            NO_RETRIEVAL → answer
            METADATA_ONLY → metadata → answer
            FULL_RAG → metadata → faiss → grade → answer
        }
    """
    graph = StateGraph(AdaptiveRAGState)

    # Add nodes
    graph.add_node("adaptive", lambda s: adaptive_node(s, llm))
    graph.add_node(
        "metadata",
        lambda s: metadata_node(s, metadata_lookup_tool, embedding_model)
    )
    graph.add_node("faiss", lambda s: faiss_node(s, yearwise_faiss_retrieval_tool, embedding_model))
    graph.add_node("grade", lambda s: grading_node(s, llm))
    graph.add_node("answer", lambda s: answer_node(s, llm))

    # Set start
    graph.set_entry_point("adaptive")

    # Adaptive decision routing
    graph.add_conditional_edges(
        "adaptive",
        lambda s: s["mode"],
        {
            "NO_RETRIEVAL": "answer",
            "METADATA_ONLY": "metadata",
            "FULL_RAG": "metadata",
        }
    )

    # Metadata conditional routing
    graph.add_conditional_edges(
        "metadata",
        lambda s: "answer" if s["mode"] == "METADATA_ONLY" else "faiss",
        {
            "answer": "answer",
            "faiss": "faiss",
        }
    )

    # FAISS → Grading → Answer
    graph.add_edge("faiss", "grade")
    graph.add_edge("grade", "answer")

    # Set finish
    graph.set_finish_point("answer")

    return graph.compile()
