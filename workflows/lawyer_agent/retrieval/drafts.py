"""
Draft Template Retrieval

Retrieves legal drafting templates and formats.
No logic, just retrieval.
"""

from typing import List, Dict, Any


def retrieve_drafts(query: str, chroma_store: Any, embedding_model=None, k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve legal drafting templates.
    
    Args:
        query: Legal context for draft
        chroma_store: langchain_chroma.Chroma store for legal drafts
        embedding_model: Not used (Chroma has embeddings built-in)
        k: Number of templates
    
    Returns:
        List of template documents
    """
    if not chroma_store:
        print("   ⚠️  Draft store not available")
        return []
    
    try:
        results = chroma_store.similarity_search(query, k=k)
        
        docs = []
        for doc in results:
            docs.append({
                "content": doc.page_content,
                "source": "legal_draft_template",
                "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
            })
        
        print(f"   ✅ Retrieved {len(docs)} draft templates")
        return docs
    except Exception as e:
        print(f"   ⚠️  Draft retrieval failed: {e}")
        return []
