"""
Test Runner for Lawyer Agent

Creates dependencies, invokes graph, displays output.

Test Questions:
    1. "Is right to privacy a fundamental right in India?"
    2. "What are the limits on freedom of speech?"
    3. "Can death penalty be imposed in murder cases?"
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from workflows.lawyer_agent.graph import build_lawyer_agent_graph
from workflows.lawyer_agent.state import LawyerState
from modules.embedding_manager import EmbeddingManager
from modules.llm_manager import LLMManager
from modules.vector_store.chroma_vector_store import ChromaVectorStore
from modules.vector_store.FAISS_vector_store import FAISSVectorStore
from langchain_chroma import Chroma


def setup_dependencies():
    """
    Initialize all dependencies.
    
    Returns:
        Dict with: llm, chroma_stores, chroma_drafts, faiss_store, embedding_model
    """
    
    print("\n⚙️  SETTING UP DEPENDENCIES...")
    
    # Embedding model
    embedding_model = EmbeddingManager()
    print("   ✅ Embeddings loaded (BAAI/bge-base-en-v1.5)")
    
    # LLM
    llm_manager = LLMManager(provider="groq", model_name="llama-3.3-70b-versatile")
    llm = llm_manager
    print("   ✅ LLM loaded (Groq llama-3.3-70b)")
    
    # Chroma stores (statutes)
    chroma_stores = {}
    
    # Constitution
    const_store = Chroma(
        collection_name="constitution",
        persist_directory="vector_db/chroma/constitution",
        embedding_function=embedding_model
    )
    chroma_stores["constitution"] = const_store
    print("   ✅ Constitution store loaded")
    
    # IPC
    ipc_store = Chroma(
        collection_name="ipc",
        persist_directory="vector_db/chroma/ipc",
        embedding_function=embedding_model
    )
    chroma_stores["ipc"] = ipc_store
    print("   ✅ IPC store loaded")
    
    # CrPC
    crpc_store = Chroma(
        collection_name="crpc",
        persist_directory="vector_db/chroma/crpc",
        embedding_function=embedding_model
    )
    chroma_stores["crpc"] = crpc_store
    print("   ✅ CrPC store loaded")
    
    # Chroma drafts
    drafts_store = Chroma(
        collection_name="legal_drafts",
        persist_directory="vector_db/chroma/legal_drafts",
        embedding_function=embedding_model
    )
    print("   ✅ Legal drafts store loaded")
    
    # FAISS store (precedents)
    faiss_store = FAISSVectorStore(embedding_model=embedding_model)
    print("   ✅ FAISS precedent store loaded")
    
    return {
        "llm": llm,
        "chroma_stores": chroma_stores,
        "chroma_drafts": drafts_store,
        "faiss_store": faiss_store,
        "embedding_model": embedding_model
    }


def run_lawyer_agent(question: str, dependencies: dict):
    """
    Run the Lawyer Agent workflow on a question.
    
    Args:
        question: Legal question
        dependencies: Initialized dependencies
    """
    
    print("\n" + "=" * 60)
    print(f"QUESTION: {question}")
    print("=" * 60)
    
    # Build graph
    graph = build_lawyer_agent_graph(dependencies)
    
    # Initial state
    initial_state = LawyerState(
        question=question,
        facts=[],
        facts_raw=[],
        analysis="",
        statutes=[],
        precedents=[],
        prediction="",
        similar_cases=[],
        prediction_confidence=0.0,
        draft="",
        templates=[],
        citations=[],
        approved_phase="",
        user_feedback="",
        reasoning_trace=[]
    )
    
    try:
        # Run workflow
        final_state = graph.invoke(initial_state)
        
        # Display results
        print("\n" + "=" * 60)
        print("📋 WORKFLOW COMPLETED")
        print("=" * 60)
        
        print("\n🔍 AUDIT TRAIL:")
        for entry in final_state.get("reasoning_trace", []):
            print(f"   {entry}")
        
        print("\n📄 FINAL DRAFT:")
        print(final_state.get("draft", "No draft generated")[:500] + "...")
        
        print("\n✅ Session complete!")
        
    except KeyboardInterrupt as e:
        print(f"\n⛔ {str(e)}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    
    # Setup
    dependencies = setup_dependencies()
    
    # Test questions
    test_questions = [
        "Is right to privacy a fundamental right in India?",
        "What are the limits on freedom of speech?",
        "Can death penalty be imposed in murder cases?",
    ]
    
    print("\n" + "=" * 60)
    print("🧑‍⚖️  LAWYER AGENT - ENTERPRISE IMPLEMENTATION")
    print("=" * 60)
    
    # Run first question (others commented out for brevity)
    run_lawyer_agent(test_questions[0], dependencies)
    
    # Uncomment to run all:
    # for question in test_questions:
    #     run_lawyer_agent(question, dependencies)
    #     print("\n\n")
