"""
Retrieval Layer - Pure RAG Functions

Implements YEARWISE FAISS scanning:
1. If target_years provided, use them directly
2. Otherwise, scan yearwise FAISS from 1950..min(current_year, 2025)
3. Aggregate results from available year indexes
4. Fallback to statutory collections (Constitution, IPC, CrPC)

NO METADATA-FIRST GATING. Direct yearwise scan ensures comprehensive retrieval.
Completely decoupled from reasoning.

This separation is critical for:
- Swappable backends
- Unit testability
- Transparent auditing
"""

from typing import List, Dict, Any


def retrieve_statutes(query: str, chroma_stores: Dict[str, Any], embedding_model=None, k: int = 6, target_years: List[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieve statutory material using YEARWISE FAISS scanning.
    
    Workflow:
        1. If target_years provided, use them directly
        2. Otherwise, scan yearwise FAISS from 1950..min(current_year, 2025)
        3. Aggregate results from all available year indexes
        4. Fallback → Constitution, IPC, CrPC statutory collections
    
    Args:
        query: Legal question
        chroma_stores: Dict of Chroma stores {"constitution", "ipc", "crpc"}
        embedding_model: Embedding model for semantic search
        k: Results per source
        target_years: Optional explicit year constraints from feedback
    
    Returns:
        List of documents with metadata
    """
    docs = []

    print("   📋 YEARWISE STATUTES RETRIEVAL (1950→latest)")
    
    # If target_years provided (from revised query feedback), use them directly
    if target_years:
        print(f"   🎯 Using explicit year constraints from feedback: {target_years}")
        years = target_years
    else:
        # ============================================
        # SCAN YEARWISE FAISS (1950→current)
        # ============================================
        from datetime import datetime
        current = datetime.now().year
        start_year = 1950
        end_year = min(current, 2025)
        years = list(range(start_year, end_year + 1))
        # Only announce yearwise FAISS scanning if an embedding_model is available
        # (when embedding_model is None we will skip FAISS and fall back to collections).
        if embedding_model:
            print(f"   🔎 Scanning yearwise FAISS for years {start_year}..{end_year} (this may take time)")


    # ============================================
    # YEARWISE FAISS RETRIEVAL
    # ============================================
    if years and embedding_model:
        print(f"   📋 Searching yearwise FAISS for {len(years)} year(s)")
        
        try:
            from modules.vector_store.FAISS_vector_store import FAISSVectorStore
            
            for year in years:
                faiss_path = f"vector_db/yearwise/{year}"
                try:
                    vs = FAISSVectorStore(embedding_model=embedding_model)
                    vs.load(faiss_path)
                    
                    year_docs = vs.similarity_search(query, k=k)
                    
                    for doc in year_docs:
                        docs.append({
                            "content": doc.page_content,
                            "source": f"yearwise_faiss_{year}",
                            "metadata": getattr(doc, 'metadata', {})
                        })
                    
                    if year_docs:
                        print(f"   ✅ Retrieved {len(year_docs)} documents from year {year}")
                
                except FileNotFoundError:
                    # index missing for this year; continue scanning
                    continue
                except Exception as e:
                    print(f"   ⚠️  Error loading year {year} FAISS: {e}")
            
            # If we got results from FAISS, return them
            if docs:
                print(f"   ✅ Total FAISS documents retrieved: {len(docs)}")
                return docs
        
        except Exception as e:
            print(f"   ⚠️  FAISS retrieval failed: {e}")

    # ============================================
    # FALLBACK: STATUTORY COLLECTIONS
    # ============================================
    print("   📋 Falling back to statutory collections (Constitution, IPC, CrPC)")
    
    for source_name in ["constitution", "ipc", "crpc"]:
        store = chroma_stores.get(source_name)
        if not store:
            continue

        try:
            # Use langchain_chroma's similarity_search
            results = store.similarity_search(query, k=k)

            for doc in results:
                docs.append({
                    "content": doc.page_content,
                    "source": source_name,
                    "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
                })
            
            print(f"   ✅ Retrieved {len(results)} sections from {source_name}")
        
        except Exception as e:
            print(f"   ⚠️  {source_name}: {e}")

    return docs
