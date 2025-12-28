"""
Precedent Retrieval - METADATA-FIRST approach

Implements METADATA-FIRST workflow for case law:
1. Query metadata store to identify relevant years
2. Decision → metadata sufficient or need targeted FAISS?
3. If needed → retrieve from yearwise FAISS indexes only
4. Fallback → global FAISS if available

Pure retrieval from Supreme Court judgments.
No reasoning, just similarity search.
"""

from typing import List, Dict, Any


def retrieve_precedents(query: str, faiss_store: Any = None, embedding_model: Any = None, k: int = 5, target_years: List[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieve relevant Supreme Court precedents using METADATA-FIRST approach.
    
    Workflow:
        1. Query metadata store → identify relevant years
        2. Decision → metadata sufficient or need targeted FAISS?
        3. If needed → retrieve from yearwise FAISS indexes
        4. Fallback → global FAISS if available
    
    Args:
        query: Legal question or analysis
        faiss_store: Global FAISS vector store instance (fallback)
        embedding_model: Embedding model for semantic search
        k: Number of results per source
    
    Returns:
        List of case documents with metadata
    """
    
    docs = []
    
    print("   🏛️  METADATA-FIRST PRECEDENT RETRIEVAL")
    
    # If explicit target_years provided (from revise feedback), use them directly
    if target_years:
        years = target_years
        print(f"   🎯 Using explicit year constraints from feedback: {years}")
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
            else:
                # Encode query
                query_embedding = embedding_model.embed_query(query)

                # Perform similarity search in metadata
                results = metadata_db.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    include=["metadatas", "distances"]
                )

                # Extract years
                years = set()

                if results and results["metadatas"] and results["metadatas"][0]:
                    for metadata in results['metadatas'][0]:
                        year = metadata.get("year")
                        if year and str(year).isdigit():
                            years.add(int(year))

                years = sorted(list(years))

                if years:
                    print(f"   ✅ Metadata lookup: Found relevant years {years}")
                else:
                    print(f"   ⚠️  Metadata lookup: No relevant years found")

        except Exception as e:
            print(f"   ⚠️  Metadata lookup failed: {e}")
            years = []

    # ============================================
    # STEP 2: YEARWISE FAISS RETRIEVAL (TARGETED)
    # ============================================
    if years and embedding_model:
        print(f"   📋 Decision: SEARCH_YEARWISE_FAISS for years {years}")
        
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
                            "source": f"precedent_year_{year}",
                            "metadata": getattr(doc, 'metadata', {})
                        })
                    
                    print(f"   ✅ Retrieved {len(year_docs)} precedents from year {year}")
                
                except FileNotFoundError:
                    print(f"   ⚠️  No FAISS store for year {year}")
                except Exception as e:
                    print(f"   ⚠️  Error loading year {year}: {e}")
            
            # If we got results, return them
            if docs:
                print(f"   ✅ Total precedents from yearwise FAISS: {len(docs)}")
                return docs
        
        except Exception as e:
            print(f"   ⚠️  Yearwise FAISS retrieval failed: {e}")

    # ============================================
    # FALLBACK: GLOBAL FAISS STORE
    # ============================================
    if faiss_store:
        print("   📋 Falling back to global FAISS store")
        
        try:
            documents = faiss_store.similarity_search(query, k=k)
            
            for doc in documents:
                docs.append({
                    "content": doc.page_content,
                    "source": "supreme_court_judgment",
                    "metadata": getattr(doc, 'metadata', {})
                })
            
            print(f"   ✅ Retrieved {len(documents)} precedents from global FAISS")
            return docs
        
        except Exception as e:
            print(f"   ⚠️  Global FAISS retrieval failed: {e}")
    else:
        print("   ⚠️  No FAISS store available")
    
    return docs
