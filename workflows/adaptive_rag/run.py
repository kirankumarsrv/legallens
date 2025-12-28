"""
Adaptive RAG Workflow Runner

Executes the complete Adaptive RAG system with intelligent routing.

Strategy:
    1. Adaptive Decision (NO_RETRIEVAL / METADATA_ONLY / FULL_RAG)
    2. Metadata Lookup (if needed)
    3. Targeted FAISS (if needed)
    4. Corrective Grading (if needed)
    5. Answer Generation
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.embedding_manager import EmbeddingManager
from modules.llm_manager import LLMManager
from workflows.adaptive_rag.graph import build_adaptive_rag_graph


def main():
    print("\n" + "=" * 70)
    print("🚀 ADAPTIVE RAG SYSTEM - INTELLIGENT ROUTING")
    print("=" * 70 + "\n")

    # 1. Initialize embeddings
    print("📦 Loading embedding model...")
    embedder = EmbeddingManager(
        model_name="BAAI/bge-base-en-v1.5",
        # device="cuda"
    )
    print("✅ Embedding model ready\n")

    # 2. Initialize LLM
    print("🤖 Loading LLM (Groq - Llama 3.3-70B)...")
    llm = LLMManager(
        provider="groq",
        model_name="llama-3.3-70b-versatile"
    )
    print("✅ LLM ready\n")

    # 3. Build graph
    print("🔗 Building Adaptive RAG graph...")
    graph = build_adaptive_rag_graph(
        llm=llm,
        embedding_model=embedder
    )
    print("✅ Graph compiled\n")

    # 4. Test queries demonstrating all three modes
    queries = [
        ("What is Article 21?", "NO_RETRIEVAL"),
        ("In which year was the Puttaswamy judgment delivered?", "METADATA_ONLY"),
        ("Explain how Article 21 was interpreted in Supreme Court judgments .", "FULL_RAG"),
    ]

    # 5. Run workflow
    print("=" * 70)
    for idx, (query, expected_mode) in enumerate(queries, 1):
        print(f"\n🟡 QUERY {idx}: {query}")
        print(f"   Expected Mode: {expected_mode}")
        print(f"   ⏳ Processing...\n")

        result = graph.invoke({"question": query})

        print(f"   ✅ Actual Mode: {result['mode']}")
        print(f"\n   📘 ANSWER:\n")
        print(f"   {result['answer']}\n")
        print("   " + "-" * 66)

    print("\n" + "=" * 70)
    print("✅ All queries processed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
