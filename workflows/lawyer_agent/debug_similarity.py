"""Debug similarity using METADATA-FIRST workflow.

This script implements the correct workflow:
1. Query metadata store (vector_db/metadata) to identify relevant years
2. Decide if metadata is sufficient OR if yearwise FAISS retrieval is needed
3. If needed, query yearwise FAISS stores based on identified years

Run from repository root:
    python -m workflows.lawyer_agent.debug_similarity
"""

from modules.embedding_manager import EmbeddingManager
from modules.vector_store.chroma_vector_store import ChromaVectorStore
from modules.vector_store.FAISS_vector_store import FAISSVectorStore

query = "Is right to privacy a fundamental right in India?"

print("\n" + "="*70)
print("METADATA-FIRST DEBUG WORKFLOW")
print("="*70)

# Initialize embedding model
try:
    emb = EmbeddingManager()
    print("\n✅ Embedding model loaded:", emb.get_model_info()["model_name"])
except Exception as e:
    print(f"\n❌ Failed to initialize EmbeddingManager: {e}")
    exit(1)

# ============================================
# STEP 1: METADATA LOOKUP (MANDATORY FIRST)
# ============================================
print(f"\n{'='*70}")
print("STEP 1: METADATA LOOKUP (vector_db/metadata)")
print(f"{'='*70}")
print(f"Query: {query}\n")

try:
    metadata_db = ChromaVectorStore(persist_dir="vector_db/metadata")
    print(f"✅ Loaded metadata store")
    
    # Encode query
    query_embedding = emb.embed_query(query)
    print(f"✅ Query encoded to embedding (dim={len(query_embedding)})")
    
    # Perform similarity search in metadata
    results = metadata_db.collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=["metadatas", "documents", "distances"]
    )
    
    years = set()
    case_names = []
    summaries = []
    
    if results and results["metadatas"] and results["metadatas"][0]:
        print(f"\n✅ Found {len(results['metadatas'][0])} metadata results:\n")
        for i, metadata in enumerate(results['metadatas'][0]):
            year = metadata.get("year")
            case_name = metadata.get("case_name", "N/A")
            summary = metadata.get("summary", "N/A")[:100] + "..."
            distance = results["distances"][0][i] if results["distances"] else "N/A"
            
            print(f"[{i}] Year: {year} | Case: {case_name}")
            print(f"    Distance: {distance} | Summary: {summary}")
            
            if year and str(year).isdigit():
                years.add(int(year))
            case_names.append(case_name)
            summaries.append(metadata.get("summary", ""))
    else:
        print("⚠️  No metadata results found!")
        years = []

except Exception as e:
    print(f"❌ Metadata lookup failed: {e}")
    exit(1)

# ============================================
# STEP 2: DECISION - IS METADATA ENOUGH?
# ============================================
print(f"\n{'='*70}")
print("STEP 2: DECISION POINT")
print(f"{'='*70}")

if summaries:
    metadata_sufficient = len(" ".join(summaries)) > 200
else:
    metadata_sufficient = False

print(f"\nRelevant years from metadata: {sorted(list(years))}")
print(f"Number of summaries: {len(summaries)}")
print(f"Total summary length: {len(' '.join(summaries)) if summaries else 0} chars")
print(f"\n🎯 Decision: {'METADATA_ONLY' if metadata_sufficient else 'NEED_YEARWISE_FAISS_RETRIEVAL'}")

# ============================================
# STEP 3: YEARWISE FAISS RETRIEVAL (IF NEEDED)
# ============================================
if not metadata_sufficient and years:
    print(f"\n{'='*70}")
    print("STEP 3: TARGETED YEARWISE FAISS RETRIEVAL")
    print(f"{'='*70}")
    
    retrieved_docs = []
    
    for year in sorted(list(years)):
        faiss_path = f"vector_db/yearwise/{year}"
        print(f"\n📂 Searching year {year} at {faiss_path}...")
        
        try:
            vs = FAISSVectorStore(embedding_model=emb)
            vs.load(faiss_path)
            print(f"   ✅ Loaded FAISS store for year {year}")
            
            docs = vs.similarity_search(query, k=3)
            print(f"   ✅ Retrieved {len(docs)} documents")
            
            for i, doc in enumerate(docs):
                content_preview = doc.page_content[:80] + "..." if len(doc.page_content) > 80 else doc.page_content
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                print(f"      [{i}] {content_preview}")
                print(f"          Metadata: {metadata}")
            
            retrieved_docs.extend(docs)
            
        except FileNotFoundError:
            print(f"   ⚠️  No FAISS store found for year {year}")
        except Exception as e:
            print(f"   ❌ Error loading year {year}: {e}")
    
    print(f"\n📊 Total documents retrieved from FAISS: {len(retrieved_docs)}")
else:
    print(f"\n{'='*70}")
    print("STEP 3: SKIPPED")
    print(f"{'='*70}")
    print("Metadata is sufficient to answer the question.")

# ============================================
# STATUTE STORES (SECONDARY - Constitution, IPC, CrPC)
# ============================================
print(f"\n{'='*70}")
print("BONUS: STATUTE STORES (Constitution, IPC, CrPC)")
print(f"{'='*70}")

for name, path in [("constitution", "vector_db/chroma/constitution"),
                   ("ipc", "vector_db/chroma/ipc"),
                   ("crpc", "vector_db/chroma/crpc")]:
    print(f"\n📋 {name.upper()} ({path})...")
    try:
        store = ChromaVectorStore(persist_dir=path)
        query_embedding = emb.embed_query(query)
        results = store.collection.query(
            query_embeddings=[query_embedding],
            n_results=2,
            include=["documents", "distances"]
        )
        
        if results and results["documents"] and results["documents"][0]:
            print(f"   ✅ Found {len(results['documents'][0])} results")
            for i, doc in enumerate(results["documents"][0]):
                preview = doc[:80] + "..." if len(doc) > 80 else doc
                print(f"      [{i}] {preview}")
        else:
            print(f"   ℹ️  No results found")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

print(f"\n{'='*70}")
print("DEBUG COMPLETE")
print(f"{'='*70}\n")