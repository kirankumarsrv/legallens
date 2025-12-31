"""
Phase 1: Fact Gathering Node

Retrieves statutory facts from multiple sources, prioritizing evidence over public law.
Includes precedent retrieval so case law can be surfaced as facts for human approval.

Like reading the FIR before going to court. Evidence (if provided) becomes the PRIMARY context.

Outputs:
 - facts: list of candidate facts (statutes, web snippets, research, precedents)
 - fact_storage: FactStorage instance
 - precedents: raw precedent docs retrieved (for UI)
 - fact_source_breakdown: counts by source
"""

from workflows.lawyer_agent.retrieval.statutes import retrieve_statutes
from workflows.lawyer_agent.retrieval.precedents import retrieve_precedents
from workflows.lawyer_agent.state import LawyerState
from modules.fact_storage import FactStorage
from modules.fact_retriever import CompositeRetriever, FactRetrieverFactory, SourceType
import os
try:
    from modules.vector_store.FAISS_vector_store import FAISSVectorStore
except Exception:
    FAISSVectorStore = None


def fact_gathering_node(
    state: LawyerState,
    chroma_stores: dict,
    embedding_model,
    faiss_store=None,
    llm=None,
    enable_web_search: bool = False,
    enable_research_papers: bool = False,
    pdf_directory: str = None
) -> LawyerState:
    """
    First phase: Gather statutory material and precedents as candidate facts.
    """

    # Initialize FactStorage if not already done
    if not state.get("fact_storage"):
        state["fact_storage"] = FactStorage()

    fact_storage = state["fact_storage"]

    print("\n📋 PHASE 1: FACT GATHERING (MULTI-SOURCE)")

    # Build query: evidence FIRST, then question
    query = state.get("question", "")
    if state.get("evidence_text"):
        query = f"""
CASE EVIDENCE (PRIMARY):
{state['evidence_text'][:1000]}

LEGAL QUESTION:
{state.get('question','')}
"""
        print(f"   📁 Evidence injected into query context ({len(state['evidence_text'])} chars)\n")

    # Extract target years if provided (from revise_action)
    target_years = None
    if state.get("revise_action") and state["revise_action"].get("constraint_years"):
        target_years = state["revise_action"]["constraint_years"]

    print("   🔍 MULTI-SOURCE RETRIEVAL")

    # Statutes from statutory collections (Chroma)
    vector_facts = retrieve_statutes(
        query=query,
        chroma_stores=chroma_stores,
        embedding_model=None,
        k=6,
        target_years=target_years,
    )

    # Diagnostic: report availability of FAISS/global store and embedding model
    try:
        print(f"   🔎 FAISS available to Phase1: {bool(faiss_store)}; embedding_model provided: {bool(embedding_model)}")
    except Exception:
        print("   🔎 FAISS diagnostic: unable to determine faiss_store/embedding_model presence")

    # Web search
    web_facts = []
    if enable_web_search:
        try:
            web_retriever = FactRetrieverFactory.create_web_search_retriever()
            web_query = state.get("question", "").replace("\n", " ")[:300]
            web_facts = web_retriever.retrieve(query=web_query, constraints={"k": 3})
        except Exception as e:
            print(f"   ⚠️  Web search failed: {e}")

    # Research papers
    paper_facts = []
    if enable_research_papers and pdf_directory:
        try:
            paper_retriever = FactRetrieverFactory.create_research_paper_retriever(pdf_directory, embedding_model)
            arxiv_query = state.get("question", "").replace("\n", " ")[:200]
            paper_facts = paper_retriever.retrieve(query=arxiv_query, constraints={"k": 3})
        except Exception as e:
            print(f"   ⚠️  Research paper retrieval failed: {e}")

    # Precedents via FAISS (include as facts for approval)
    precs = []
    precedent_facts = []
    try:
        if faiss_store or embedding_model:
            try:
                precs = retrieve_precedents(
                    query=query,
                    faiss_store=faiss_store,
                    embedding_model=embedding_model,
                    k=1,
                    target_years=target_years,
                )
            except Exception as e:
                print(f"   ⚠️  Precedent retrieval failed in Phase 1: {e}")
                precs = []

            for p in precs:
                raw_text = p.get("content", "") or ""
                metadata = p.get("metadata", {}) or {}

                # Minimal snippet (300 chars) for quick lawyer review
                snippet = (raw_text[:300] + "…") if len(raw_text) > 300 else raw_text

                # LLM evaluates relevance + generates summary (or filters out irrelevant cases)
                llm_summary = None
                is_relevant = True
                if llm is not None:
                    try:
                        # Combined prompt: evaluate relevance AND summarize if relevant
                        eval_prompt = f"""Given the following legal question and a court judgment excerpt, determine if this case is relevant/important to the question. If relevant, provide a 1-2 sentence summary. If NOT relevant, respond with exactly "NOT_RELEVANT".

**LEGAL QUESTION:**
{state.get('question', 'Unknown')[:300]}

**COURT JUDGMENT EXCERPT:**
{raw_text}

**INSTRUCTION:**
- If this case is IMPORTANT and directly relevant to the question, provide a 1-2 sentence summary of the core facts and holding.
- If this case is NOT relevant or not important to the question, respond with exactly: NOT_RELEVANT
- Be strict: only include cases that are clearly helpful."""

                        response = llm.generate(eval_prompt, temperature=0.0, max_tokens=150)
                        if response and "NOT_RELEVANT" in response.upper():
                            is_relevant = False
                        else:
                            # Use response as summary
                            if response:
                                llm_summary = response.strip().replace("\n", " ")[:150]
                    except Exception:
                        llm_summary = None
                        is_relevant = True  # Default: include if LLM evaluation fails

                # Only add fact if relevant
                if not is_relevant:
                    print(f"      🚫 Filtered out irrelevant precedent")
                    continue

                # Build structured source details so lawyer can see origin
                source_details = {
                    "case_name": metadata.get("case_name") or metadata.get("title") or metadata.get("case_title"),
                    "year": p.get("year") or metadata.get("year"),
                    "doc_id": metadata.get("doc_id") or metadata.get("id") or metadata.get("file_id"),
                    "source_type": "precedent_faiss",
                    "score": float(p.get("score", metadata.get("score", 0.0))) if (p.get("score") is not None or metadata.get("score") is not None) else None,
                }

                relevance = source_details.get("score") if source_details.get("score") is not None else 0.75

                precedent_facts.append({
                    "content": snippet,
                    "llm_summary": llm_summary,
                    "source": "precedent",
                    "source_type": "precedent_faiss",
                    "source_details": source_details,
                    "relevance_score": float(relevance),
                })
        else:
            # Fallback: if no embedding model or global faiss_store, attempt to load yearwise FAISS indexes from disk
            try:
                yearwise_dir = os.path.join("vector_db", "yearwise")
                if FAISSVectorStore and os.path.isdir(yearwise_dir):
                    # Use same target_years logic as retrieve_precedents
                    from datetime import datetime
                    current = datetime.now().year
                    start_year = 1950
                    end_year = min(current, 2025)
                    years = list(range(start_year, end_year + 1)) if not target_years else sorted(target_years)
                    for year in years:
                        faiss_path = os.path.join(yearwise_dir, str(year))
                        if not os.path.isdir(faiss_path):
                            continue
                        try:
                            vs = FAISSVectorStore(embedding_model=embedding_model)
                            vs.load(faiss_path)
                            # retrieve only 1 doc per year to surface a concise candidate
                            year_docs = vs.similarity_search(query, k=1)
                            for doc in year_docs:
                                content_text = getattr(doc, 'page_content', None) or str(doc)
                                precs.append({
                                    "content": content_text,
                                    "source": f"precedent_year_{year}",
                                    "metadata": getattr(doc, 'metadata', {}),
                                    "year": year,
                                    "score": getattr(doc, 'score', None)
                                })
                            if year_docs:
                                print(f"   ✅ Retrieved {len(year_docs)} precedents from year {year} (fallback)")
                        except Exception as e:
                            print(f"   ⚠️  Could not load/search FAISS for year {year}: {e}")
                    if precs:
                        for p in precs:
                            raw_text = p.get("content", "") or ""
                            metadata = p.get("metadata", {}) or {}

                            snippet = (raw_text[:300] + "…") if len(raw_text) > 300 else raw_text

                            # LLM evaluates relevance + generates summary (or filters out irrelevant cases)
                            llm_summary = None
                            is_relevant = True
                            if llm is not None:
                                try:
                                    eval_prompt = f"""Given the following legal question and a court judgment excerpt, determine if this case is relevant/important to the question. If relevant, provide a 1-2 sentence summary. If NOT relevant, respond with exactly "NOT_RELEVANT".

**LEGAL QUESTION:**
{state.get('question', 'Unknown')[:300]}

**COURT JUDGMENT EXCERPT:**
{raw_text}

**INSTRUCTION:**
- If this case is IMPORTANT and directly relevant to the question, provide a 1-2 sentence summary of the core facts and holding.
- If this case is NOT relevant or not important to the question, respond with exactly: NOT_RELEVANT
- Be strict: only include cases that are clearly helpful."""

                                    response = llm.generate(eval_prompt, temperature=0.0, max_tokens=150)
                                    if response and "NOT_RELEVANT" in response.upper():
                                        is_relevant = False
                                    else:
                                        if response:
                                            llm_summary = response.strip().replace("\n", " ")[:150]
                                except Exception:
                                    llm_summary = None
                                    is_relevant = True

                            if not is_relevant:
                                continue

                            source_details = {
                                "case_name": metadata.get("case_name") or metadata.get("title") or metadata.get("case_title"),
                                "year": p.get("year") or metadata.get("year") or year,
                                "doc_id": metadata.get("doc_id") or metadata.get("id") or metadata.get("file_id"),
                                "source_type": "precedent_faiss",
                                "score": float(p.get("score", metadata.get("score", 0.0))) if (p.get("score") is not None or metadata.get("score") is not None) else None,
                            }

                            relevance = source_details.get("score") if source_details.get("score") is not None else 0.75

                            precedent_facts.append({
                                "content": snippet,
                                "llm_summary": llm_summary,
                                "source": "precedent",
                                "source_type": "precedent_faiss",
                                "source_details": source_details,
                                "relevance_score": float(relevance),
                            })
            except Exception:
                # silent fallback
                pass
    except Exception:
        precs = []
        precedent_facts = []

    # Aggregate
    all_facts = vector_facts + web_facts + paper_facts + precedent_facts

    # Breakdown
    fact_source_breakdown = {
        "vector_store": len(vector_facts),
        "web_search": len(web_facts),
        "research_paper": len(paper_facts),
        "manual": 0,
        "precedent": len(precedent_facts),
    }

    print(f"   ✅ Retrieved {len(all_facts)} facts (vector:{len(vector_facts)}, web:{len(web_facts)}, papers:{len(paper_facts)}, precedents:{len(precedent_facts)})")

    # Store facts in FactStorage
    for fact in all_facts:
        fact_storage.add_fact(
            content=fact.get("content", ""),
            source=fact.get("source", "unknown"),
            source_details={
                "source_type": fact.get("source_type"),
                "statute_section": fact.get("source_details", {}).get("statute_section") if fact.get("source_details") else None,
                "url": fact.get("source_details", {}).get("url") if fact.get("source_details") else None,
                "file": fact.get("source_details", {}).get("file") if fact.get("source_details") else None,
                "full_metadata": fact.get("metadata", {}),
                "llm_summary": fact.get("llm_summary") if fact.get("llm_summary") else None,
            },
            relevance_score=fact.get("relevance_score", 0.7),
        )

    # Update state
    state["facts"] = all_facts
    state["facts_raw"] = [f.get("content") for f in all_facts]
    state["fact_storage"] = fact_storage
    state["facts_approved_and_locked"] = False
    state["fact_source_breakdown"] = fact_source_breakdown
    state["precedents"] = precs

    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    state["reasoning_trace"].append(f"PHASE 1: Retrieved {len(all_facts)} facts from multiple sources (stored in FactStorage)")

    print("\n   ✅ Facts stored in FactStorage (pending approval)")
    print(f"   🔒 Facts are NOT locked. Lawyer approval needed to freeze them.\n")
    return state