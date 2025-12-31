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


def retrieve_precedents(query: str, faiss_store: Any = None, embedding_model: Any = None, k: int = 1, target_years: List[int] = None) -> List[Dict[str, Any]]:
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
    
    print("   🏛️  YEARWISE PRECEDENT RETRIEVAL (1950→latest)")
    
    # If explicit target_years provided (from revise feedback), use them directly
    if target_years:
        years = sorted(target_years)
        print(f"   🎯 Using explicit year constraints from feedback: {years}")
    else:
        # ============================================
        # NEW: Direct yearwise FAISS scan from 1950 → current_year
        # We intentionally avoid metadata-first lookups and search all
        # yearwise FAISS indexes. This may take longer but returns
        # more facts for the lawyer to review.
        # ============================================
        from datetime import datetime
        current = datetime.now().year
        start_year = 1950
        end_year = min(current, 2025)
        years = list(range(start_year, end_year + 1))
        print(f"   🔎 Scanning yearwise FAISS for years {start_year}..{end_year} (this may take time)")

    # ============================================
    # STEP 2: YEARWISE FAISS RETRIEVAL (TARGETED)
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

                    # retrieve only `k` results per year (default 1)
                    year_docs = vs.similarity_search(query, k=k)

                    for doc in year_docs:
                        docs.append({
                            "content": doc.page_content,
                            "source": f"precedent_year_{year}",
                            "metadata": getattr(doc, 'metadata', {}),
                            "year": year
                        })

                    if year_docs:
                        print(f"   ✅ Retrieved {len(year_docs)} precedents from year {year}")

                except FileNotFoundError:
                    # no index for this year; continue scanning
                    continue
                except Exception as e:
                    print(f"   ⚠️  Error loading year {year}: {str(e)[:80]}")
            
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
