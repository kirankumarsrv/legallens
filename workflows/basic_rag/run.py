"""
Basic RAG Workflow Runner

Executes the complete RAG workflow with embedding model, retriever, and LLM.
"""

import os
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.embedding_manager import EmbeddingManager
from modules.llm_manager import LLMManager
from workflows.basic_rag.retriever import get_retriever
from workflows.basic_rag.graph import build_rag_graph


# Configuration
FAISS_PATH = "vector_db/yearwise/1965"  # example path
DB_TYPE = "faiss"                       # "faiss" or "chroma"
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
LLM_PROVIDER = "groq"
LLM_MODEL = "llama-3.3-70b-versatile"


def main():
    print("\n🚀 Starting Basic RAG Workflow...\n")

    # 1. Initialize embedding model
    print("📦 Loading embedding model...")
    embedder = EmbeddingManager(
        model_name=EMBEDDING_MODEL,
        # device="cuda"
    )
    print(f"✅ Embedding model loaded: {EMBEDDING_MODEL}\n")

    # 2. Initialize retriever
    print(f"📚 Loading {DB_TYPE.upper()} vector store from {FAISS_PATH}...")
    retriever = get_retriever(
        db_type=DB_TYPE,
        path=FAISS_PATH,
        embedding_model=embedder,
        k=3
    )
    print("✅ Retriever initialized\n")

    # 3. Initialize LLM
    print(f"🤖 Loading LLM ({LLM_PROVIDER}/{LLM_MODEL})...")
    llm = LLMManager(
        provider=LLM_PROVIDER,
        model_name=LLM_MODEL
    )
    print("✅ LLM initialized\n")

    # 4. Build graph
    print("🔗 Building RAG graph...")
    graph = build_rag_graph(retriever, llm)
    print("✅ Graph compiled\n")

    # 5. User question
    query = "What did the Supreme Court say about Article 21 in 1965?"

    # 6. Execute graph
    print(f"❓ Question: {query}\n")
    print("⏳ Processing...\n")
    
    result = graph.invoke({"question": query})

    # 7. Display results
    print("=" * 50)
    print("📘 FINAL ANSWER:\n")
    print(result["answer"])
    print("=" * 50 + "\n")
    
    # Optional: Display retrieved documents
    print(f"📄 Retrieved {len(result['retrieved_docs'])} documents:\n")
    for i, doc in enumerate(result["retrieved_docs"], 1):
        print(f"{i}. {doc.metadata if hasattr(doc, 'metadata') else 'No metadata'}")
        print(f"   {doc.page_content[:100]}...\n")


if __name__ == "__main__":
    main()
