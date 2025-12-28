"""
Corrective RAG Workflow Runner

Executes the Self-RAG pattern: retrieve → grade → answer

This demonstrates how adding a grading step improves RAG quality.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.embedding_manager import EmbeddingManager
from modules.llm_manager import LLMManager
from workflows.corrective_rag.retriever import retrieve_chunks
from workflows.corrective_rag.grader import grade_documents
from workflows.corrective_rag.graph import build_corrective_rag_graph


def main():
    print("\n" + "=" * 70)
    print("🚀 CORRECTIVE RAG (SELF-RAG) - Retrieve → Grade → Answer")
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
    print("🔗 Building Corrective RAG graph...")
    graph = build_corrective_rag_graph(
        retriever_fn=retrieve_chunks,
        grader_fn=grade_documents,
        llm=llm,
        embedding_model=embedder
    )
    print("✅ Graph compiled\n")

    # 4. Example query
    question = "Explain the scope of Article 21"
    year = 1965

    # 5. Run workflow
    print("=" * 70)
    print(f"\n❓ Question: {question}")
    print(f"📅 Year: {year}\n")
    print("⏳ Processing (retrieve → grade → answer)...\n")

    result = graph.invoke({
        "question": question,
        "year": year
    })

    # 6. Display results
    print("\n" + "=" * 70)
    print("📊 RETRIEVAL & GRADING SUMMARY:")
    print(f"   • Retrieved: {len(result['retrieved_docs'])} documents")
    print(f"   • Filtered: {len(result['filtered_docs'])} relevant documents")
    if result['retrieved_docs']:
        ratio = len(result['filtered_docs']) / len(result['retrieved_docs'])
        print(f"   • Precision: {ratio*100:.1f}%")
    print("\n" + "=" * 70)

    print("\n📘 FINAL ANSWER:\n")
    print(result["answer"])
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
