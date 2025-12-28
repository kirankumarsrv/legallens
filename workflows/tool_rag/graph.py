"""
Tool-RAG Graph Module

Defines the metadata-first LangGraph workflow.

Flow:
    metadata_node → decision_node → (answer_node OR faiss_node → answer_node)
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

    # metadata stage
    years: List[int]
    case_names: List[str]
    summaries: List[str]
    pdf_paths: List[str]

    # decision
    metadata_only: bool
    selected_years: List[int]

    # retrieval
    retrieved_docs: List[Document]

    # final
    answer: str


# -------------------------
# NODE 1: METADATA LOOKUP
# -------------------------
def metadata_node(state: ToolRAGState, metadata_tool, embedding_model):
    """
    First node: Always query metadata store.
    
    This is mandatory and ALWAYS executes first.
    Retrieves high-level information to guide routing.
    """
    metadata = metadata_tool(state["question"], embedding_model)
    return {
        "years": metadata["years"],
        "case_names": metadata["case_names"],
        "summaries": metadata["summaries"],
        "pdf_paths": metadata["pdf_paths"]
    }


# -------------------------
# NODE 2: DECISION MAKER
# -------------------------
def decision_node(state: ToolRAGState, llm):
    """
    Second node: Decide whether metadata alone is sufficient.
    
    Uses LLM to determine:
    - METADATA_ONLY: Answer directly from metadata summaries
    - FAISS_REQUIRED: Perform targeted FAISS retrieval
    """

    prompt = f"""You are a legal assistant making a routing decision.

Question:
{state['question']}

Available metadata summaries:
{chr(10).join(state['summaries'])}

Decide: Can the question be answered ONLY from these metadata summaries?

If YES, output exactly: METADATA_ONLY
If NO (you need detailed content), output exactly: FAISS_REQUIRED

Decision:"""

    decision = llm.generate(prompt).strip()

    if "METADATA_ONLY" in decision:
        return {
            "metadata_only": True,
            "selected_years": []
        }

    # else FAISS required
    return {
        "metadata_only": False,
        "selected_years": state["years"]
    }


# -------------------------
# NODE 3: TARGETED FAISS
# -------------------------
def faiss_node(state: ToolRAGState, faiss_tool, embedding_model):
    """
    Third node (conditional): Perform targeted FAISS retrieval.
    
    Only executes if metadata_only = False.
    Loads FAISS indexes ONLY for selected years.
    """
    docs = faiss_tool(
        query=state["question"],
        years=state["selected_years"],
        embedding_model=embedding_model
    )

    return {"retrieved_docs": docs}


# -------------------------
# NODE 4: ANSWER GENERATION
# -------------------------
def answer_node(state: ToolRAGState, llm):
    """
    Final node: Generate answer using metadata OR FAISS docs.
    
    Context source:
    - If metadata_only=True: Use summaries
    - If metadata_only=False: Use full FAISS documents
    """

    if state["metadata_only"]:
        context = "\n\n".join(state["summaries"])
        context_source = "metadata summaries"
    else:
        context = "\n\n".join(d.page_content for d in state["retrieved_docs"])
        context_source = "detailed documents"

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
    metadata_tool,
    faiss_tool,
    embedding_model
):
    """
    Construct the complete Tool-RAG workflow.
    
    Nodes:
        1. metadata → mandatory metadata lookup
        2. decide → routing decision (metadata or FAISS)
        3. faiss → conditional FAISS retrieval
        4. answer → final answer generation
    
    Flow:
        metadata → decide → (answer OR faiss) → answer
    """
    graph = StateGraph(ToolRAGState)

    # Add nodes
    graph.add_node("metadata", lambda s: metadata_node(s, metadata_tool, embedding_model))
    graph.add_node("decide", lambda s: decision_node(s, llm))
    graph.add_node("faiss", lambda s: faiss_node(s, faiss_tool, embedding_model))
    graph.add_node("answer", lambda s: answer_node(s, llm))

    # Set start
    graph.set_entry_point("metadata")

    # Connect metadata → decide
    graph.add_edge("metadata", "decide")

    # Conditional routing from decide
    graph.add_conditional_edges(
        "decide",
        lambda s: "answer" if s["metadata_only"] else "faiss",
        {
            "answer": "answer",
            "faiss": "faiss"
        }
    )

    # Connect faiss → answer
    graph.add_edge("faiss", "answer")

    # Set finish
    graph.set_finish_point("answer")

    return graph.compile()
