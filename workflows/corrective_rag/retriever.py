"""
Corrective RAG Retriever Module

Performs baseline FAISS retrieval with high recall.
Precision is handled by the grader in the next step.
"""

from typing import List
from langchain_core.documents import Document
from modules.vector_store.FAISS_vector_store import FAISSVectorStore


def retrieve_chunks(
    query: str,
    embedding_model,
    year: int,
    k: int = 8
) -> List[Document]:
    """
    Perform initial broad retrieval from year-wise FAISS index.
    
    Design philosophy:
        - High recall (k=8 retrieves more chunks)
        - Low precision (we don't filter yet)
        - Precision is fixed by the grader in the next step
    
    Args:
        query (str): User's question
        embedding_model: Embedding model instance
        year (int): Year to search in
        k (int): Number of chunks to retrieve (default 8 for high recall)
    
    Returns:
        List[Document]: Unfiltered retrieved documents
    """

    faiss_path = f"vector_db/yearwise/{year}"

    try:
        vs = FAISSVectorStore(embedding_model)
        vs.load(faiss_path)
        
        docs = vs.similarity_search(query, k=k)
        return docs
    except Exception as e:
        print(f"⚠️  Could not retrieve from year {year}: {e}")
        return []
