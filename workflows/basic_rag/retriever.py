"""
Basic RAG Retriever Module

Loads FAISS or Chroma vector stores and exposes retriever functions.
"""

import os
from langchain_chroma import Chroma
from langchain_community.vectorstores import FAISS


def load_chroma(path, embedding_model, k=4):
    """
    Load Chroma vector store as a retriever.
    
    Args:
        path: Path to Chroma vector store directory
        embedding_model: Embedding model instance
        k: Number of top results to retrieve
    
    Returns:
        Retriever instance
    """
    vectordb = Chroma(
        persist_directory=path,
        embedding_function=embedding_model
    )
    return vectordb.as_retriever(
        search_kwargs={"k": k}
    )


def load_faiss(path, embedding_model, k=4):
    """
    Load FAISS vector store as a retriever.
    
    Args:
        path: Path to FAISS vector store directory
        embedding_model: Embedding model instance
        k: Number of top results to retrieve
    
    Returns:
        Retriever instance
    """
    vectordb = FAISS.load_local(
        folder_path=path,
        embeddings=embedding_model,
        allow_dangerous_deserialization=True
    )
    return vectordb.as_retriever(
        search_kwargs={"k": k}
    )


def get_retriever(db_type: str, path: str, embedding_model, k=4):
    """
    Return the correct retriever based on db_type.
    
    Args:
        db_type: Type of vector store ("faiss" or "chroma")
        path: Path to vector store directory
        embedding_model: Embedding model instance
        k: Number of top results to retrieve
    
    Returns:
        Retriever instance
    
    Raises:
        ValueError: If db_type is not 'faiss' or 'chroma'
    """
    if db_type == "faiss":
        return load_faiss(path, embedding_model, k)
    elif db_type == "chroma":
        return load_chroma(path, embedding_model, k)
    else:
        raise ValueError("db_type must be 'faiss' or 'chroma'")
