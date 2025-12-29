"""
Phase 1: Fact Gathering Node

Retrieves statutory facts from multiple sources, prioritizing evidence over public law.
NO case law, NO interpretation at this stage.

Like reading the FIR before going to court.
Evidence (if provided) becomes the PRIMARY context.

NEW: Uses multi-source retriever (vector stores, web search, research papers, manual input)
NEW: Uses FactStorage to prevent duplicate retrieval and track approval status
"""

from workflows.lawyer_agent.retrieval.statutes import retrieve_statutes
from workflows.lawyer_agent.state import LawyerState
from modules.fact_storage import FactStorage
from modules.fact_retriever import CompositeRetriever, FactRetrieverFactory, SourceType


def fact_gathering_node(
    state: LawyerState,
    chroma_stores: dict,
    embedding_model,
    enable_web_search: bool = False,
    enable_research_papers: bool = False,
    pdf_directory: str = None
) -> LawyerState:
    """
    First phase: Gather statutory material from multiple sources.
    
    Inputs from state:
        - question: User's legal question
        - evidence_text: Parsed text from case files (optional)
    
    Inputs from function:
        - chroma_stores: Dictionary of vector stores (statutes, precedents)
        - embedding_model: Embedding model instance
        - enable_web_search: Include web search results
        - enable_research_papers: Include research paper search
        - pdf_directory: Directory with research PDFs
    
    Outputs to state:
        - facts: Retrieved facts from all sources (for display)
        - fact_storage: FactStorage instance with facts & approval tracking
        - facts_approved_and_locked: False initially (set to True after approval)
        - fact_source_breakdown: Count of facts by source
        - reasoning_trace: Audit trail
    
    Philosophy:
        ✔ Multiple sources (vectors, web, papers, manual input)
        ✔ Evidence FIRST (if provided)
        ✔ Facts only (no opinions)
        ✔ Pure retrieval (no logic)
        ✔ NEW: Store facts with approval status to prevent re-retrieval
        ✔ NEW: Deduplication & ranking across sources
    """
    
    # Initialize FactStorage if not already done
    if not state.get("fact_storage"):
        state["fact_storage"] = FactStorage()
    
    fact_storage = state["fact_storage"]
    
    print("\n📋 PHASE 1: FACT GATHERING (MULTI-SOURCE)")
    print("   Objectives:")
    print("   - Retrieve facts from multiple sources (vectors, web, papers, manual)")
    print("   - Extract key entities (parties, dates, legal issues)")
    print("   - Retrieve applicable statutes (Constitution, IPC, CrPC)")
    print("   - Establish factual timeline")
    print("   - Prioritize EVIDENCE over public law")
    print("   - Deduplicate and rank by relevance\n")
    
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
    
    # ============================================================
    # STEP 1: Vector Store Retrieval (statutes & precedents)
    # ============================================================
    print("   🔍 MULTI-SOURCE RETRIEVAL")
    print("   " + "=" * 50)
    
    # Retrieve statutes from vector stores
    vector_facts = retrieve_statutes(
        query=query,
        chroma_stores=chroma_stores,
        embedding_model=embedding_model,
        k=6,
        target_years=target_years
    )
    
    fact_source_breakdown = {"vector_store": 0, "web_search": 0, "research_paper": 0, "manual": 0}
    fact_source_breakdown["vector_store"] = len(vector_facts)
    
    print(f"   ✅ Retrieved {len(vector_facts)} facts from vector stores (statutes/precedents)")
    
    # ============================================================
    # STEP 2: Web Search Retrieval (optional)
    # ============================================================
    web_facts = []
    if enable_web_search:
        try:
            web_retriever = FactRetrieverFactory.create_web_search_retriever()
            web_facts = web_retriever.retrieve(
                query=query,
                constraints={"k": 3}
            )
            fact_source_breakdown["web_search"] = len(web_facts)
            print(f"   ✅ Retrieved {len(web_facts)} facts from web search")
        except Exception as e:
            print(f"   ⚠️  Web search failed: {e}")
    
    # ============================================================
    # STEP 3: Research Paper Retrieval (optional)
    # ============================================================
    paper_facts = []
    if enable_research_papers and pdf_directory:
        try:
            paper_retriever = FactRetrieverFactory.create_research_paper_retriever(
                pdf_directory,
                embedding_model
            )
            paper_facts = paper_retriever.retrieve(
                query=query,
                constraints={"k": 3}
            )
            fact_source_breakdown["research_paper"] = len(paper_facts)
            print(f"   ✅ Retrieved {len(paper_facts)} facts from research papers")
        except Exception as e:
            print(f"   ⚠️  Research paper retrieval failed: {e}")
    
    # ============================================================
    # STEP 4: Aggregate all facts into FactStorage
    # ============================================================
    all_facts = vector_facts + web_facts + paper_facts
    
    print(f"\n   📊 FACT AGGREGATION")
    print(f"   Total facts retrieved: {len(all_facts)}")
    print(f"   Source breakdown: {fact_source_breakdown}\n")
    
    # Store facts in FactStorage with metadata
    for fact in all_facts:
        fact_storage.add_fact(
            content=fact.get("content", ""),
            source=fact.get("source", "unknown"),
            source_details={
                "source_type": fact.get("source_type"),
                "statute_section": fact.get("source_details", {}).get("statute_section"),
                "url": fact.get("source_details", {}).get("url"),
                "file": fact.get("source_details", {}).get("file"),
                "full_metadata": fact.get("metadata", {})
            },
            relevance_score=fact.get("relevance_score", 0.7)
        )
    
    # Update state
    state["facts"] = all_facts
    state["facts_raw"] = [f.get("content") for f in all_facts]
    state["fact_storage"] = fact_storage
    state["facts_approved_and_locked"] = False  # Not locked until approved
    state["fact_source_breakdown"] = fact_source_breakdown
    
    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    
    state["reasoning_trace"].append(
        f"PHASE 1: Retrieved {len(all_facts)} facts from multiple sources (stored in FactStorage)"
    )
    state["reasoning_trace"].append(
        f"   → Vector stores: {fact_source_breakdown['vector_store']}"
    )
    if enable_web_search:
        state["reasoning_trace"].append(
            f"   → Web search: {fact_source_breakdown['web_search']}"
        )
    if enable_research_papers:
        state["reasoning_trace"].append(
            f"   → Research papers: {fact_source_breakdown['research_paper']}"
        )
    
    print("\n   ✅ Facts stored in FactStorage (pending approval)")
    print(f"   🔒 Facts are NOT locked. Lawyer approval needed to freeze them.\n")
