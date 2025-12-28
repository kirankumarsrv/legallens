"""
Tool-RAG Tools Module

Implements metadata-first retrieval strategy:
1. Metadata lookup - identify relevant years and cases
2. Targeted FAISS - retrieve only from selected years
"""

from typing import List, Dict
from langchain_core.documents import Document

from modules.vector_store.chroma_vector_store import ChromaVectorStore
from modules.vector_store.FAISS_vector_store import FAISSVectorStore


# -------------------------------------------------
# TOOL 1: METADATA LOOKUP (MANDATORY FIRST STEP)
# -------------------------------------------------
def metadata_lookup_tool(query: str, embedding_model, limit: int = 5) -> Dict:
    """
    Retrieve high-level metadata to decide routing using semantic search.
    
    Metadata lookup is ALWAYS the first step to identify:
    - Relevant years
    - Case names
    - Case summaries
    - PDF paths

    Args:
        query (str): User's question
        embedding_model: Embedding model to encode the query
        limit (int): Number of metadata results to retrieve

    Returns:
        Dict with keys:
            - years: List of relevant years
            - case_names: List of case names
            - summaries: List of case summaries
            - pdf_paths: List of PDF file paths
    """

    metadata_db = ChromaVectorStore(persist_dir="vector_db/metadata")
    
    # Use semantic search on metadata collection
    query_embedding = embedding_model.embed_query(query)
    
    # Query using embeddings
    results = metadata_db.collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        include=["metadatas", "documents", "distances"]
    )

    years = set()
    case_names = []
    summaries = []
    pdf_paths = []

    # Process results
    if results and results["metadatas"]:
        for metadata_list in results["metadatas"]:
            for metadata in metadata_list:
                if "year" in metadata and str(metadata.get("year", "")).isdigit():
                    years.add(int(metadata["year"]))
                case_names.append(metadata.get("case_name", ""))
                summaries.append(metadata.get("summary", ""))
                pdf_paths.append(metadata.get("pdf_path", ""))

    return {
        "years": sorted(list(years)),
        "case_names": case_names,
        "summaries": summaries,
        "pdf_paths": pdf_paths
    }


# -------------------------------------------------
# TOOL 2: TARGETED FAISS RETRIEVAL
# -------------------------------------------------
def yearwise_faiss_retrieval_tool(
    query: str,
    years: List[int],
    embedding_model,
    k: int = 4
) -> List[Document]:
    """
    Perform FAISS retrieval ONLY on selected year indexes.
    
    FAISS is NEVER global - loaded only for selected years.
    This ensures:
    - Memory efficiency
    - Faster retrieval
    - Accurate results for targeted searches

    Args:
        query (str): User's question
        years (List[int]): Selected years to search
        embedding_model: Embedding model instance
        k (int): Number of results per year

    Returns:
        List[Document]: Combined retrieved documents from selected years
    """

    retrieved_docs = []

    for year in years:
        try:
            faiss_path = f"vector_db/yearwise/{year}"
            
            vs = FAISSVectorStore(embedding_model)
            vs.load(faiss_path)
            
            docs = vs.similarity_search(query, k=k)
            retrieved_docs.extend(docs)
        except Exception as e:
            print(f"⚠️  Could not load FAISS for year {year}: {e}")
            continue

    return retrieved_docs
