"""
Corrective RAG Grader Module

LLM-based document relevance grading (Self-RAG style).
Filters out irrelevant chunks before answer generation.
"""

from typing import List
from langchain_core.documents import Document


def grade_documents(
    question: str,
    documents: List[Document],
    llm,
    threshold: float = 0.5
) -> List[Document]:
    """
    Grade retrieved documents for relevance using LLM.
    
    This is the core of Corrective RAG.
    For each document, the LLM decides: RELEVANT or IRRELEVANT
    
    Design philosophy:
        - Simple binary classification (RELEVANT / IRRELEVANT)
        - Can be extended with scores or confidence
        - Significantly reduces hallucinations
    
    Args:
        question (str): User's question
        documents (List[Document]): Retrieved documents to grade
        llm: LLM manager instance
        threshold (float): Confidence threshold (unused in binary classification)
    
    Returns:
        List[Document]: Filtered documents (only RELEVANT ones)
    """

    relevant_docs = []

    for idx, doc in enumerate(documents, 1):
        prompt = f"""You are a legal document relevance grader.

Question:
{question}

Document:
{doc.page_content}

Is this document RELEVANT to answering the question?

Respond with ONLY one word: RELEVANT or IRRELEVANT
"""

        decision = llm.generate(prompt).strip().upper()

        if "RELEVANT" in decision:
            relevant_docs.append(doc)
            print(f"   ✅ Doc {idx}: RELEVANT")
        else:
            print(f"   ❌ Doc {idx}: IRRELEVANT (filtered out)")

    return relevant_docs
