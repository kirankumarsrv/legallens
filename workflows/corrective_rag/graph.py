"""
Corrective RAG Graph Module

Defines the Self-RAG workflow: retrieve → grade → answer

This implements the Corrective RAG pattern where documents are graded
for relevance before answer generation.
"""

from typing import TypedDict, List
from langgraph.graph import StateGraph
from langchain_core.documents import Document


# -------------------------
# STATE SCHEMA
# -------------------------
class CorrectiveRAGState(TypedDict):
    """State schema for Corrective RAG workflow."""
    question: str
    year: int

    # retrieval stage
    retrieved_docs: List[Document]

    # grading stage
    filtered_docs: List[Document]

    # final
    answer: str


# -------------------------
# NODE 1: RETRIEVE
# -------------------------
def retrieve_node(state: CorrectiveRAGState, retriever_fn, embedding_model):
    """
    First node: Retrieve documents broadly.
    
    High recall, low precision - grader will filter next.
    """
    docs = retriever_fn(
        query=state["question"],
        embedding_model=embedding_model,
        year=state["year"]
    )
    return {"retrieved_docs": docs}


# -------------------------
# NODE 2: GRADE
# -------------------------
def grade_node(state: CorrectiveRAGState, grader_fn, llm):
    """
    Second node: Grade documents for relevance.
    
    LLM evaluates each document and keeps only RELEVANT ones.
    This is the correction step that improves answer quality.
    """
    filtered = grader_fn(
        question=state["question"],
        documents=state["retrieved_docs"],
        llm=llm
    )
    return {"filtered_docs": filtered}


# -------------------------
# NODE 3: ANSWER
# -------------------------
def answer_node(state: CorrectiveRAGState, llm):
    """
    Final node: Generate answer using only filtered documents.
    
    Now we have high-confidence, relevant chunks only.
    This reduces hallucinations and improves factual accuracy.
    """
    context = "\n\n".join(d.page_content for d in state["filtered_docs"])

    prompt = f"""You are a legal assistant answering based on Indian law.
Answer ONLY using the provided context. Do not add external knowledge.

Context (from graded documents):
{context if context else "No relevant documents found."}

Question:
{state['question']}

Answer:"""

    answer = llm.generate(prompt)
    return {"answer": answer}


# -------------------------
# BUILD GRAPH
# -------------------------
def build_corrective_rag_graph(
    retriever_fn,
    grader_fn,
    llm,
    embedding_model
):
    """
    Construct the Corrective RAG workflow.
    
    Nodes:
        1. retrieve → broad FAISS search (high recall)
        2. grade → LLM relevance grading (increase precision)
        3. answer → answer generation (high confidence)
    
    Flow:
        retrieve → grade → answer
    
    Key insight:
        Cheap, fast retrieval + smart filtering = better results than
        trying to make retrieval perfect in the first place.
    """
    graph = StateGraph(CorrectiveRAGState)

    # Add nodes
    graph.add_node("retrieve", lambda s: retrieve_node(s, retriever_fn, embedding_model))
    graph.add_node("grade", lambda s: grade_node(s, grader_fn, llm))
    graph.add_node("answer", lambda s: answer_node(s, llm))

    # Define flow
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_edge("grade", "answer")
    graph.set_finish_point("answer")

    return graph.compile()
