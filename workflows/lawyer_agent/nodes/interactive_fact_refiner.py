from typing import Dict, Any

from modules.fact_retriever import FactRetrieverFactory
from modules.fact_storage import FactStorage


def retrieve_facts_node(state: Dict[str, Any], chroma_stores: Dict[str, Any], embedding_model, enable_web_search: bool = True, enable_research_papers: bool = False, pdf_directory: str = None) -> Dict[str, Any]:
    """Retrieve facts from multiple sources and store them in state's FactStorage.

    This node avoids re-retrieval when facts are already approved and locked.
    """
    # Ensure fact_storage exists on state
    if state.get("fact_storage") is None:
        state["fact_storage"] = FactStorage()

    fact_storage: FactStorage = state["fact_storage"]

    # If facts already approved & locked, skip retrieval
    if state.get("facts_approved_and_locked") or fact_storage.is_facts_approved_and_locked():
        print("ℹ️  Facts already approved and locked — skipping retrieval.")
        state["facts"] = fact_storage.get_all_facts()
        return state

    # Build composite retriever
    composite = FactRetrieverFactory.create_composite_retriever(
        embedding_model,
        vector_stores=chroma_stores,
        enable_web_search=enable_web_search,
        enable_research_papers=enable_research_papers,
        pdf_directory=pdf_directory,
    )

    query = state.get("question") or state.get("evidence_text") or ""
    if not query:
        print("⚠️  No query or evidence text available for fact retrieval.")
        return state

    # Retrieve facts (top 100 to allow human pruning)
    retrieved = composite.retrieve(query, constraints={"k": 100})

    # Add retrieved facts to storage (avoid duplicates via FactStorage logic)
    fact_storage.add_facts_batch(retrieved)
    state["facts"] = fact_storage.get_all_facts()

    print(f"✅ Retrieved {len(retrieved)} facts and stored in FactStorage (total={len(state['facts'])}).")

    return state


def fact_display_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare facts for display (UI or console). Returns state unchanged but ensures facts list present."""
    fs = state.get("fact_storage")
    if not fs:
        state["facts"] = []
        return state

    # Provide summary in state for UI layers
    state["facts_summary"] = fs.get_summary_stats()
    state["facts"] = fs.get_all_facts()
    return state


def per_fact_chat_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder node for per-fact interactive editing.

    In a UI integration this node would surface each fact for edit/delete/keep.
    Here we leave facts as-is so the human approval gate can act on them.
    """
    # No-op for headless runs; facts remain pending until approval
    return state


def fact_approval_node(state: Dict[str, Any], llm=None, embedding_model=None) -> Dict[str, Any]:
    """Wrap the existing human approval gate for facts to lock approved facts in storage."""
    fs: FactStorage = state.get("fact_storage")
    if not fs:
        print("⚠️  No FactStorage present at approval time.")
        return state

    # The human_approval_node is expected to modify state (approved ids etc.)
    # After approval, lock approved facts to prevent re-retrieval
    if fs.is_facts_approved_and_locked():
        state["facts_approved_and_locked"] = True
        return state

    # If approvals were done externally (e.g., UI), lock them now
    fs.lock_approved_facts()
    state["facts_approved_and_locked"] = True
    state["facts"] = fs.get_all_facts()

    print("✅ Approved facts locked and ready for legal analysis.")
    return state
