"""
Tool-RAG Graph Module

Defines the yearwise FAISS LangGraph workflow.

Flow:
    yearwise_faiss_node → answer_node
    
No mandatory metadata lookup; direct yearwise scanning from 1950..2025.
"""

from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document


# -------------------------
# STATE SCHEMA
# -------------------------
class ToolRAGState(TypedDict):
    """State schema for Tool-RAG workflow."""
    question: str

    # yearwise retrieval
    selected_years: List[int]

    # retrieval
    retrieved_docs: List[Document]

    # final
    answer: str


# -------------------------
# NODE 1: YEARWISE FAISS RETRIEVAL
# -------------------------
def yearwise_faiss_node(state: ToolRAGState, faiss_tool, embedding_model):
    """
    First node: Perform yearwise FAISS retrieval.
    
    Scans yearwise FAISS indexes from 1950..min(current_year, 2025).
    Aggregates documents from all available year indexes.
    If no years provided, scans full range.
    """
    from datetime import datetime
    
    current = datetime.now().year
    start_year = 1950
    end_year = min(current, 2025)
    years = list(range(start_year, end_year + 1))
    
    docs = faiss_tool(
        query=state["question"],
        years=years,
        embedding_model=embedding_model
    )

    return {
        "selected_years": years,
        "retrieved_docs": docs
    }


# -------------------------
# NODE 2: ANSWER GENERATION
# -------------------------
def answer_node(state: ToolRAGState, llm):
    """
    Final node: Generate answer using yearwise FAISS docs.
    
    Context source: Full FAISS documents from yearwise scanning.
    """

    context = "\n\n".join(d.page_content for d in state["retrieved_docs"])
    context_source = f"yearwise FAISS documents ({len(state['retrieved_docs'])} docs)"

    prompt = f"""You are a legal assistant answering based on Indian law.
Answer ONLY using the provided context. Do not add external knowledge.

Context ({context_source}):
{context}

Question:
{state['question']}

Answer:"""

    answer = llm.generate(prompt)

    return {"answer": answer}


# -------------------------
# BUILD GRAPH
# -------------------------
def build_tool_rag_graph(
    llm,
    faiss_tool,
    embedding_model
):
    """
    Construct the complete Tool-RAG workflow.
    
    Nodes:
        1. yearwise_faiss → scan yearwise FAISS (1950..2025)
        2. answer → final answer generation
    
    Flow:
        yearwise_faiss → answer
    
    No mandatory metadata lookup; direct yearwise scanning ensures comprehensive retrieval.
    """
    graph = StateGraph(ToolRAGState)

    # Add nodes
    graph.add_node("yearwise_faiss", lambda s: yearwise_faiss_node(s, faiss_tool, embedding_model))
    graph.add_node("answer", lambda s: answer_node(s, llm))

    # Set start
    graph.set_entry_point("yearwise_faiss")

    # Connect yearwise_faiss → answer
    graph.add_edge("yearwise_faiss", "answer")

    # Set finish
    graph.set_finish_point("answer")

    return graph.compile()
