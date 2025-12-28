"""
Retrieval Layer - Pure RAG Functions

Implements METADATA-FIRST workflow:
1. Query metadata store to identify relevant years
2. Decide if metadata is sufficient
3. If needed, perform targeted yearwise FAISS retrieval
4. Fallback to statutory collections (Constitution, IPC, CrPC)

NO LOGIC. Only retrieval.
Completely decoupled from reasoning.

This separation is critical for:
- Swappable backends
- Unit testability
- Transparent auditing
"""

from typing import List, Dict, Any


def retrieve_statutes(query: str, chroma_stores: Dict[str, Any], embedding_model=None, k: int = 6, target_years: List[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieve statutory material using METADATA-FIRST workflow.
    
    Workflow:
        1. Query metadata store → identify relevant years
        2. Decision → metadata sufficient or need yearwise FAISS?
        3. If needed → targeted FAISS retrieval from relevant years
        4. Fallback → Constitution, IPC, CrPC statutory collections
    
    Args:
        query: Legal question
        chroma_stores: Dict of Chroma stores {"constitution", "ipc", "crpc"}
        embedding_model: Embedding model for semantic search
        k: Results per source
    
    Returns:
        List of documents with metadata
    """
    docs = []

    print("   📂 METADATA-FIRST RETRIEVAL")
    
    # If target_years provided (from revised query feedback), use them directly
    if target_years:
        print(f"   🎯 Using explicit year constraints from feedback: {target_years}")
        years = target_years
        metadata_sufficient = False  # Force yearwise FAISS retrieval
    else:
        # ============================================
        # STEP 1: METADATA LOOKUP (MANDATORY FIRST)
        # ============================================
        try:
            from modules.vector_store.chroma_vector_store import ChromaVectorStore
            
            metadata_db = ChromaVectorStore(persist_dir="vector_db/metadata")
            
            if not embedding_model:
                print("   ⚠️  No embedding model provided. Skipping metadata lookup.")
                years = []
                metadata_sufficient = False
            else:
                # Encode query
                query_embedding = embedding_model.embed_query(query)
                
                # Perform similarity search in metadata
                results = metadata_db.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    include=["metadatas", "documents", "distances"]
                )
                
                # Extract years and summaries
                years = set()
                summaries = []
                
                if results and results["metadatas"] and results["metadatas"][0]:
                    for metadata in results['metadatas'][0]:
                        year = metadata.get("year")
                        if year and str(year).isdigit():
                            years.add(int(year))
                        summaries.append(metadata.get("summary", ""))
                
                years = sorted(list(years))
                
                # ============================================
                # STEP 2: DECISION - IS METADATA ENOUGH?
                # ============================================
                total_summary_length = len(" ".join(summaries)) if summaries else 0
                metadata_sufficient = total_summary_length > 200
                
                if years:
                    print(f"   ✅ Metadata lookup: Found {len(results['metadatas'][0])} results from years {years}")
                else:
                    print(f"   ⚠️  Metadata lookup: No relevant years found")
                    metadata_sufficient = False
        
        except Exception as e:
            print(f"   ⚠️  Metadata lookup failed: {e}")
            years = []
            metadata_sufficient = False

    # ============================================
    # STEP 3: YEARWISE FAISS RETRIEVAL (IF NEEDED)
    # ============================================
    if not metadata_sufficient and years:
        print(f"   📋 Decision: NEED_YEARWISE_FAISS_RETRIEVAL for years {years}")
        
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
                    
                    print(f"   ✅ Retrieved {len(year_docs)} documents from year {year} FAISS")
                
                except FileNotFoundError:
                    print(f"   ⚠️  No FAISS store found for year {year}")
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
