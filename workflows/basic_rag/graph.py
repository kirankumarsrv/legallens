"""
Basic RAG Graph Module

Defines the LangGraph workflow for a minimal RAG system.
Graph flow: retrieve → generate → answer
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_core.documents import Document


# --------------------
# Define state schema
# --------------------
class RAGState(TypedDict):
    """State schema for RAG workflow."""
    question: str
    retrieved_docs: List[Document]
    answer: str


# --------------------
# Node: Retriever
# --------------------
def retrieve_node(state: RAGState, retriever):
    """
    Retrieve relevant chunks from vectorstore based on the question.
    
    Args:
        state: Current RAG state
        retriever: Retriever instance
    
    Returns:
        Updated state with retrieved documents
    """
    docs = retriever.invoke(state["question"])
    return {"retrieved_docs": docs}


# --------------------
# Node: Generator (LLM)
# --------------------
def generate_node(state: RAGState, llm):
    """
    Use LLM to answer question using retrieved docs.
    
    Args:
        state: Current RAG state
        llm: LLM manager instance
    
    Returns:
        Updated state with generated answer
    """
    context = "\n\n".join([doc.page_content for doc in state["retrieved_docs"]])

    prompt = f"""You are a helpful legal assistant. Use ONLY the given context to answer.

Context:
{context}

Question:
{state['question']}

Answer:"""

    output = llm.generate(prompt)
    return {"answer": output}


# --------------------
# Build Graph
# --------------------
def build_rag_graph(retriever, llm):
    """
    Create a basic RAG graph with LangGraph.
    
    Args:
        retriever: Retriever instance
        llm: LLM manager instance
    
    Returns:
        Compiled LangGraph graph
    """
    graph = StateGraph(RAGState)

    # Add nodes
    graph.add_node("retrieve", lambda state: retrieve_node(state, retriever))
    graph.add_node("generate", lambda state: generate_node(state, llm))

    # Define flow
    graph.add_edge("retrieve", "generate")
    graph.set_entry_point("retrieve")
    graph.set_finish_point("generate")

    return graph.compile()
