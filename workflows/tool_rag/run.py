"""
Tool-RAG Workflow Runner

Executes the metadata-first Tool-RAG system.

Strategy:
    1. Metadata lookup (mandatory)
    2. Decision node (metadata sufficient?)
    3. Targeted FAISS retrieval (if needed)
    4. Answer generation
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.embedding_manager import EmbeddingManager
from modules.llm_manager import LLMManager
from workflows.tool_rag.tools import (
    metadata_lookup_tool,
    yearwise_faiss_retrieval_tool
)
from workflows.tool_rag.graph import build_tool_rag_graph


def main():
    print("\n" + "=" * 60)
    print("🚀 METADATA-FIRST TOOL-RAG SYSTEM")
    print("=" * 60 + "\n")

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
    print("🔗 Building Tool-RAG graph...")
    graph = build_tool_rag_graph(
        llm=llm,
        metadata_tool=metadata_lookup_tool,
        faiss_tool=yearwise_faiss_retrieval_tool,
        embedding_model=embedder
    )
    print("✅ Graph compiled\n")

    # 4. Example query
    query = "Explain the interpretation of Article 21 in Supreme Court judgments."

    # 5. Run workflow
    print(f"❓ Question: {query}\n")
    print("⏳ Processing (metadata → decision → retrieval → answer)...\n")

    result = graph.invoke({
        "question": query
    })

    # 6. Display results
    print("=" * 60)
    print("📘 FINAL ANSWER")
    print("=" * 60 + "\n")
    print(result["answer"])
    print("\n" + "=" * 60)

    # 7. Show metadata (optional)
    print("\n📊 METADATA RETRIEVED:")
    print(f"   • Years: {result['years']}")
    print(f"   • Cases: {len(result['case_names'])}")
    print(f"   • Metadata-only decision: {result['metadata_only']}")
    if not result['metadata_only']:
        print(f"   • Documents retrieved: {len(result['retrieved_docs'])}")
    print("\n✅ Done\n")


if __name__ == "__main__":
    main()
