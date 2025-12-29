"""
Phase 1: Fact Gathering Node

Retrieves statutory facts, prioritizing evidence over public law.
NO case law, NO interpretation at this stage.

Like reading the FIR before going to court.
Evidence (if provided) becomes the PRIMARY context.

NEW: Uses FactStorage to prevent duplicate retrieval and track approval status.
"""

from workflows.lawyer_agent.retrieval.statutes import retrieve_statutes
from workflows.lawyer_agent.state import LawyerState
from modules.fact_storage import FactStorage


def fact_gathering_node(state: LawyerState, chroma_stores: dict, embedding_model) -> LawyerState:
    """
    First phase: Gather statutory material, prioritizing private evidence.
    
    Inputs from state:
        - question: User's legal question
        - evidence_text: Parsed text from case files (optional)
    
    Outputs to state:
        - facts: Retrieved statutory documents (for display)
        - fact_storage: FactStorage instance with facts & approval tracking
        - facts_approved_and_locked: False initially (set to True after approval)
        - reasoning_trace: Audit trail
    
    Philosophy:
        ✔ Evidence FIRST (if provided)
        ✔ Facts only (no opinions)
        ✔ Statutes only (no cases)
        ✔ Pure retrieval (no logic)
        ✔ NEW: Store facts with approval status to prevent re-retrieval
    """
    
    # Initialize FactStorage if not already done
    if not state.get("fact_storage"):
        state["fact_storage"] = FactStorage()
    
    fact_storage = state["fact_storage"]
    
    print("\n📋 PHASE 1: FACT GATHERING")
    print("   Objectives:")
    print("   - Extract key entities (parties, dates, legal issues)")
    print("   - Retrieve applicable statutes (Constitution, IPC, CrPC)")
    print("   - Establish factual timeline")
    print("   - Prioritize EVIDENCE over public law\n")
    
    # Build query: evidence FIRST, then question
    query = state["question"]
    if state.get("evidence_text"):
        query = f"""
CASE EVIDENCE (PRIMARY):
{state['evidence_text'][:1000]}

LEGAL QUESTION:
{state['question']}
"""
        print(f"   📁 Evidence injected into query context ({len(state['evidence_text'])} chars)\n")

    # If entities were extracted, include them to help targeted retrieval
    if state.get("entities"):
        try:
            entities_summary = {k: [e['text'] for e in v] for k, v in state['entities'].items()}
            # For persons, also include roles if available
            if "persons" in state['entities']:
                entities_summary["persons_with_roles"] = [
                    f"{p['text']} ({p.get('role', 'unknown')})" 
                    for p in state['entities']['persons']
                ]
        except Exception:
            entities_summary = str(state.get('entities'))

        query += f"\n\nEXTRACTED ENTITIES:\n{entities_summary}\n"
        print(f"   🧾 Entities injected into query: {', '.join(state['entities'].keys())}\n")
    
    # If timeline was constructed, summarize key events
    if state.get("timeline"):
        timeline_summary = []
        for event in state['timeline']:
            date = event.get('date', 'Unknown')
            persons = ", ".join(event.get('persons', [])[:2])  # First 2 persons
            summary = f"{date}: {event.get('event', '')[:80]}"
            if persons:
                summary += f" [with {persons}]"
            timeline_summary.append(summary)
        
        query += "\n\nCHRONOLOGICAL TIMELINE:\n"
        for summary in timeline_summary[:5]:  # First 5 events
            query += f"  • {summary}\n"
        if len(timeline_summary) > 5:
            query += f"  ... and {len(timeline_summary) - 5} more events\n"
        
        print(f"   📅 Timeline injected into query: {len(state['timeline'])} events\n")
    
    # Extract target years if provided (from revise_action)
    target_years = None
    if state.get("revise_action") and state["revise_action"].get("constraint_years"):
        target_years = state["revise_action"]["constraint_years"]
        print(f"   🎯 Using revised year constraints: {target_years}\n")
    
    # Retrieve statutes
    facts = retrieve_statutes(
        query=query,
        chroma_stores=chroma_stores,
        embedding_model=embedding_model,
        k=6,
        target_years=target_years
    )
    
    # Store facts in FactStorage with metadata
    for fact in facts:
        fact_storage.add_fact(
            content=fact.get("content", ""),
            source=fact.get("source", "statutes"),
            source_details={
                "statute_section": fact.get("metadata", {}).get("section"),
                "statute_type": fact.get("metadata", {}).get("statute_type"),
                "full_metadata": fact.get("metadata", {})
            },
            relevance_score=0.7  # Default relevance
        )
    
    # Update state
    state["facts"] = facts
    state["facts_raw"] = [f.get("content") for f in facts]
    state["fact_storage"] = fact_storage
    state["facts_approved_and_locked"] = False  # Not locked until approved
    
    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    
    state["reasoning_trace"].append(
        f"PHASE 1: Retrieved {len(facts)} statute sections (stored in FactStorage)"
    )
    
    return state
