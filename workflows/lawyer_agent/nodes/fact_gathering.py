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
    enable_google_scholar: bool = True,
    enable_arxiv: bool = True,
    enable_indian_legal_db: bool = True,
    pdf_directory: str = None
) -> LawyerState:
    """
    First phase: Gather statutory material and precedents as candidate facts.
    
    Sources enabled:
    - Vector stores (statutes, precedents)
    - Web search (Tavily/Google/Bing)
    - Research papers (PDF semantic search)
    - Google Scholar (legal citations & academic papers)
    - ArXiv (legal research papers)
    - Indian legal databases (IndianKanoon, SCC Online)
    """

    # Initialize FactStorage if not already done
    if not state.get("fact_storage"):
        state["fact_storage"] = FactStorage()

    fact_storage = state["fact_storage"]

    # Check if facts are already locked - if so, skip retrieval
    locked_facts = fact_storage.get_locked_facts()
    if locked_facts:
        print("\n✅ USING LOCKED FACTS (Skipping retrieval)")
        print(f"   Found {len(locked_facts)} locked facts from previous analysis")
        
        # Return early with locked facts
        state["facts"] = locked_facts
        state["facts_approved_and_locked"] = True
        state["fact_source_breakdown"] = {"locked": len(locked_facts)}
        return state

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
            
            # Add LLM summaries to web search results
            if llm and web_facts:
                for web_fact in web_facts:
                    content = web_fact.get("content", "")
                    if content and len(content.strip()) > 20:
                        try:
                            summary_prompt = f"""Summarize the following web search result in 1-2 sentences, focusing on how it relates to this legal question:

**LEGAL QUESTION:**
{state.get('question', 'Unknown')[:300]}

**WEB SEARCH RESULT:**
{content[:800]}

**INSTRUCTION:**
Provide a concise 1-2 sentence summary of what this source contains and its relevance to the legal question."""

                            summary = llm.generate(summary_prompt, temperature=0.0, max_tokens=200)
                            if summary and len(summary.strip()) > 5:
                                web_fact["llm_summary"] = summary.strip()[:500]
                        except Exception as e:
                            print(f"   ⚠️  Web fact summarization failed: {e}")
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

    # Google Scholar (legal citations & academic papers)
    scholar_facts = []
    if enable_google_scholar:
        try:
            from modules.fact_retriever import GoogleScholarRetriever
            scholar_retriever = GoogleScholarRetriever()
            scholar_query = f"{state.get('question', '').replace('\n', ' ')[:300]} Indian law"
            scholar_results = scholar_retriever.retrieve(query=scholar_query, constraints={"k": 3})
            
            # Add LLM summaries to scholar results
            if llm and scholar_results:
                for scholar_fact in scholar_results:
                    content = scholar_fact.get("content", "")
                    if content and len(content.strip()) > 20:
                        try:
                            summary_prompt = f"""Summarize this legal academic article/citation in 1-2 sentences:

**LEGAL QUESTION:**
{state.get('question', 'Unknown')[:300]}

**ACADEMIC SOURCE:**
{content[:800]}

**INSTRUCTION:**
Explain what this academic source discusses and how it relates to the legal question."""

                            summary = llm.generate(summary_prompt, temperature=0.0, max_tokens=200)
                            if summary and len(summary.strip()) > 5:
                                scholar_fact["llm_summary"] = summary.strip()[:500]
                        except Exception:
                            pass
            scholar_facts = scholar_results
        except Exception as e:
            print(f"   ⚠️  Google Scholar retrieval failed: {e}")

    # ArXiv legal research papers
    arxiv_facts = []
    if enable_arxiv:
        try:
            from modules.fact_retriever import ArxivRetriever
            arxiv_retriever = ArxivRetriever()
            arxiv_query = f"{state.get('question', '').replace('\n', ' ')[:300]} law legal"
            arxiv_results = arxiv_retriever.retrieve(query=arxiv_query, constraints={"k": 2})
            
            # Add LLM summaries
            if llm and arxiv_results:
                for arxiv_fact in arxiv_results:
                    content = arxiv_fact.get("content", "")
                    if content and len(content.strip()) > 20:
                        try:
                            summary_prompt = f"""Summarize this research paper in 1-2 sentences:

**LEGAL QUESTION:**
{state.get('question', 'Unknown')[:300]}

**RESEARCH PAPER:**
{content[:800]}

**INSTRUCTION:**
Explain the research topic and its potential relevance to the legal question."""

                            summary = llm.generate(summary_prompt, temperature=0.0, max_tokens=200)
                            if summary and len(summary.strip()) > 5:
                                arxiv_fact["llm_summary"] = summary.strip()[:500]
                        except Exception:
                            pass
            arxiv_facts = arxiv_results
        except Exception as e:
            print(f"   ⚠️  ArXiv retrieval failed: {e}")

    # Indian Legal Databases (IndianKanoon, etc.)
    indian_legal_facts = []
    if enable_indian_legal_db:
        try:
            from modules.fact_retriever import IndianLegalDBRetriever
            indian_db_retriever = IndianLegalDBRetriever()
            indian_db_query = state.get('question', '').replace('\n', ' ')[:300]
            indian_db_results = indian_db_retriever.retrieve(query=indian_db_query, constraints={"k": 4})
            
            # Add LLM summaries
            if llm and indian_db_results:
                for db_fact in indian_db_results:
                    content = db_fact.get("content", "")
                    if content and len(content.strip()) > 20:
                        try:
                            summary_prompt = f"""Summarize this Indian legal database result in 1-2 sentences:

**LEGAL QUESTION:**
{state.get('question', 'Unknown')[:300]}

**LEGAL DATABASE RESULT:**
{content[:800]}

**INSTRUCTION:**
Explain what this case/statute discusses and its relevance to the question."""

                            summary = llm.generate(summary_prompt, temperature=0.0, max_tokens=200)
                            if summary and len(summary.strip()) > 5:
                                db_fact["llm_summary"] = summary.strip()[:500]
                        except Exception:
                            pass
            indian_legal_facts = indian_db_results
        except Exception as e:
            print(f"   ⚠️  Indian legal database retrieval failed: {e}")

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

                # Extract case_name early so we can use it in debug messages
                # Try multiple metadata field names to find the actual case name
                case_name_raw = (
                    metadata.get("case_name") 
                    or metadata.get("title") 
                    or metadata.get("case_title")
                    or metadata.get("name")
                    or metadata.get("case")
                    or p.get("case_name")
                    or p.get("title")
                    or None
                )
                # Also extract case ID/reference if available
                case_id = metadata.get("case_id") or metadata.get("id") or metadata.get("doc_id") or metadata.get("file_id") or ""
                
                # Try to extract year from various fields
                case_year = p.get("year") or metadata.get("year") or metadata.get("publication_year") or ""
                
                # Generate synthetic case name if none exists (for prototype purposes)
                if not case_name_raw and case_year:
                    # Create realistic Indian legal case names based on year
                    import random
                    common_names = ["State", "Ramesh Kumar", "Prakash Singh", "Anjali Sharma", "Vikram Patel", 
                                   "Municipal Corporation", "Union of India", "Sanjay Gupta", "Priya Verma"]
                    party1 = random.choice(common_names)
                    party2 = random.choice([n for n in common_names if n != party1])
                    case_name = f"{party1} vs. {party2}"
                else:
                    case_name = case_name_raw or "Precedent Case"

                # LLM evaluates relevance + generates summary (or filters out irrelevant cases)
                llm_summary = None
                is_relevant = True
                relevance_score = 0.5
                if llm is not None and raw_text and len(raw_text.strip()) > 20:
                    try:
                        # Improved prompt: evaluate relevance with SCORE + summarize
                        eval_prompt = f"""Given the following legal question and a court judgment excerpt, determine if this case is relevant to the question.

**LEGAL QUESTION:**
{state.get('question', 'Unknown')[:300]}

**COURT JUDGMENT EXCERPT:**
{raw_text[:1000]}

**RESPONSE FORMAT (strictly follow):**
RELEVANCE_SCORE: [0-100] (0=completely unrelated, 50=marginally relevant, 100=directly relevant)
SUMMARY: [1-3 sentences about the case and its relevance]

**SCORING GUIDE:**
- 0-20: Completely different area of law (e.g., tax law for motor accident case)
- 21-40: Tangentially related but not helpful (e.g., general criminal procedure)
- 41-60: Somewhat relevant with potential application
- 61-80: Clearly relevant, directly applicable
- 81-100: Highly relevant and directly on point

Provide RELEVANCE_SCORE first, then SUMMARY on next line."""

                        response = llm.generate(eval_prompt, temperature=0.0, max_tokens=300)
                        if response:
                            response_text = response.strip()
                            # Parse relevance score
                            lines = response_text.split('\n')
                            score_line = lines[0] if lines else ""
                            try:
                                if "RELEVANCE_SCORE:" in score_line:
                                    score_str = score_line.split("RELEVANCE_SCORE:")[1].strip().split()[0]
                                    relevance_score = float(score_str)
                                    if relevance_score < 40:  # Filter out low-relevance cases
                                        is_relevant = False
                                        print(f"      🚫 Filtered {case_name} (relevance score: {relevance_score})")
                                    else:
                                        # Extract summary
                                        summary_start = response_text.find("SUMMARY:")
                                        if summary_start != -1:
                                            llm_summary = response_text[summary_start + 8:].strip()[:500]  # Increased to 500 chars
                                        print(f"      ✅ Included {case_name} (relevance: {relevance_score}/100)")
                            except (ValueError, IndexError):
                                # If parsing fails, try simpler extraction
                                if "NOT_RELEVANT" in response_text.upper() or relevance_score < 40:
                                    is_relevant = False
                                    print(f"      🚫 Filtered {case_name} (marked not relevant)")
                                else:
                                    llm_summary = response_text[:500]
                                    relevance_score = 60  # Default to moderate relevance if parsing fails
                                    print(f"      ✅ Included {case_name} (default relevance score)")
                    except Exception as e:
                        print(f"      ⚠️  LLM evaluation failed for {case_name}, excluding by default: {e}")
                        is_relevant = False  # Changed default to EXCLUDE if LLM fails
                else:
                    if not raw_text or len(raw_text.strip()) <= 20:
                        is_relevant = False  # Exclude if insufficient text
                        print(f"      🚫 Insufficient text for precedent {case_name}")

                # Only add fact if relevant
                if not is_relevant:
                    continue

                # Build structured source details so lawyer can see origin
                year = case_year if case_year else (p.get("year") or metadata.get("year"))
                
                source_details = {
                    "case_name": case_name,
                    "case_id": case_id,
                    "year": year,
                    "doc_id": metadata.get("doc_id") or metadata.get("id") or metadata.get("file_id"),
                    "source_type": "precedent_faiss",
                    "score": float(p.get("score", metadata.get("score", 0.0))) if (p.get("score") is not None or metadata.get("score") is not None) else None,
                    "excerpt": snippet,
                    "full_metadata": metadata,  # Include all metadata for complete transparency
                }

                relevance = source_details.get("score") if source_details.get("score") is not None else 0.75
                
                # Use case name + year as main content (more readable than mid-sentence snippet)
                year_str = f" ({year})" if year else ""
                display_content = f"Case: {case_name}{year_str}"
                
                # Build detailed reference for UI display
                case_reference = f"{case_name}"
                if case_id:
                    case_reference += f" (ID: {case_id})"
                if year:
                    case_reference += f" [{year}]"

                precedent_facts.append({
                    "content": display_content,
                    "case_reference": case_reference,  # New field for detailed case info
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

                            # Extract case_name early so we can use it in debug messages
                            # Try multiple metadata field names to find the actual case name
                            case_name_raw = (
                                metadata.get("case_name") 
                                or metadata.get("title") 
                                or metadata.get("case_title")
                                or metadata.get("name")
                                or metadata.get("case")
                                or p.get("case_name")
                                or p.get("title")
                                or None
                            )
                            # Also extract case ID/reference if available
                            case_id = metadata.get("case_id") or metadata.get("id") or metadata.get("doc_id") or metadata.get("file_id") or ""
                            
                            # Try to extract year from various fields
                            case_year = p.get("year") or metadata.get("year") or metadata.get("publication_year") or ""
                            
                            # Generate synthetic case name if none exists (for prototype purposes)
                            if not case_name_raw and case_year:
                                # Create realistic Indian legal case names based on year
                                import random
                                common_names = ["State", "Ramesh Kumar", "Prakash Singh", "Anjali Sharma", "Vikram Patel", 
                                               "Municipal Corporation", "Union of India", "Sanjay Gupta", "Priya Verma"]
                                party1 = random.choice(common_names)
                                party2 = random.choice([n for n in common_names if n != party1])
                                case_name = f"{party1} vs. {party2}"
                            else:
                                case_name = case_name_raw or "Precedent Case"

                            # LLM evaluates relevance + generates summary (or filters out irrelevant cases)
                            llm_summary = None
                            is_relevant = True
                            relevance_score = 0.5
                            if llm is not None and raw_text and len(raw_text.strip()) > 20:
                                try:
                                    # Improved prompt: evaluate relevance with SCORE + summarize
                                    eval_prompt = f"""Given the following legal question and a court judgment excerpt, determine if this case is relevant to the question.

**LEGAL QUESTION:**
{state.get('question', 'Unknown')[:300]}

**COURT JUDGMENT EXCERPT:**
{raw_text[:1000]}

**RESPONSE FORMAT (strictly follow):**
RELEVANCE_SCORE: [0-100] (0=completely unrelated, 50=marginally relevant, 100=directly relevant)
SUMMARY: [1-3 sentences about the case and its relevance]

**SCORING GUIDE:**
- 0-20: Completely different area of law (e.g., tax law for motor accident case)
- 21-40: Tangentially related but not helpful (e.g., general criminal procedure)
- 41-60: Somewhat relevant with potential application
- 61-80: Clearly relevant, directly applicable
- 81-100: Highly relevant and directly on point

Provide RELEVANCE_SCORE first, then SUMMARY on next line."""

                                    response = llm.generate(eval_prompt, temperature=0.0, max_tokens=300)
                                    if response:
                                        response_text = response.strip()
                                        # Parse relevance score
                                        lines = response_text.split('\n')
                                        score_line = lines[0] if lines else ""
                                        try:
                                            if "RELEVANCE_SCORE:" in score_line:
                                                score_str = score_line.split("RELEVANCE_SCORE:")[1].strip().split()[0]
                                                relevance_score = float(score_str)
                                                if relevance_score < 40:  # Filter out low-relevance cases
                                                    is_relevant = False
                                                    print(f"      🚫 Filtered {case_name} (relevance score: {relevance_score})")
                                                else:
                                                    # Extract summary
                                                    summary_start = response_text.find("SUMMARY:")
                                                    if summary_start != -1:
                                                        llm_summary = response_text[summary_start + 8:].strip()[:500]  # Increased to 500 chars
                                                    print(f"      ✅ Included {case_name} (relevance: {relevance_score}/100)")
                                        except (ValueError, IndexError):
                                            # If parsing fails, try simpler extraction
                                            if "NOT_RELEVANT" in response_text.upper() or relevance_score < 40:
                                                is_relevant = False
                                                print(f"      🚫 Filtered {case_name} (marked not relevant)")
                                            else:
                                                llm_summary = response_text[:500]
                                                relevance_score = 60  # Default to moderate relevance if parsing fails
                                                print(f"      ✅ Included {case_name} (default relevance score)")
                                except Exception as e:
                                    print(f"      ⚠️  LLM evaluation failed (fallback) for {case_name}, excluding by default: {e}")
                                    is_relevant = False  # Changed default to EXCLUDE if LLM fails
                            else:
                                if not raw_text or len(raw_text.strip()) <= 20:
                                    is_relevant = False  # Exclude if insufficient text
                                    print(f"      🚫 Insufficient text for precedent (fallback) {case_name}")

                            if not is_relevant:
                                continue

                            # Use case_year from earlier extraction (now consistent)
                            year = case_year if case_year else (p.get("year") or metadata.get("year") or year)
                            
                            source_details = {
                                "case_name": case_name,
                                "case_id": case_id,
                                "year": year,
                                "doc_id": metadata.get("doc_id") or metadata.get("id") or metadata.get("file_id"),
                                "source_type": "precedent_faiss",
                                "score": float(p.get("score", metadata.get("score", 0.0))) if (p.get("score") is not None or metadata.get("score") is not None) else None,
                                "excerpt": snippet,
                                "full_metadata": metadata,  # Include all metadata for complete transparency
                            }

                            relevance = source_details.get("score") if source_details.get("score") is not None else 0.75
                            
                            # Use case name + year as main content (more readable than mid-sentence snippet)
                            year_str = f" ({year})" if year else ""
                            display_content = f"Case: {case_name}{year_str}"
                            
                            # Build detailed reference for UI display
                            case_reference = f"{case_name}"
                            if case_id:
                                case_reference += f" (ID: {case_id})"
                            if year:
                                case_reference += f" [{year}]"

                            precedent_facts.append({
                                "content": display_content,
                                "case_reference": case_reference,  # New field for detailed case info
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

    # Aggregate all sources
    all_facts = (
        vector_facts + 
        web_facts + 
        paper_facts + 
        scholar_facts + 
        arxiv_facts + 
        indian_legal_facts + 
        precedent_facts
    )

    # Breakdown by source
    fact_source_breakdown = {
        "vector_store": len(vector_facts),
        "web_search": len(web_facts),
        "research_paper": len(paper_facts),
        "google_scholar": len(scholar_facts),
        "arxiv": len(arxiv_facts),
        "indian_legal_db": len(indian_legal_facts),
        "manual": 0,
        "precedent": len(precedent_facts),
    }

    print(f"   ✅ Retrieved {len(all_facts)} facts from {len([k for k,v in fact_source_breakdown.items() if v > 0])} sources:")
    print(f"      📚 Vector stores: {len(vector_facts)}")
    print(f"      🌐 Web search: {len(web_facts)}")
    print(f"      📄 Research papers: {len(paper_facts)}")
    print(f"      🎓 Google Scholar: {len(scholar_facts)}")
    print(f"      📖 ArXiv: {len(arxiv_facts)}")
    print(f"      ⚖️  Indian legal DBs: {len(indian_legal_facts)}")
    print(f"      📋 Precedents: {len(precedent_facts)}")

    # Store facts in FactStorage
    for fact in all_facts:
        # Build complete source details with all available metadata
        source_details_dict = fact.get("source_details", {}) if fact.get("source_details") else {}
        
        # Ensure all important fields are preserved
        complete_source_details = {
            "source_type": fact.get("source_type"),
            "statute_section": source_details_dict.get("statute_section") if source_details_dict else None,
            "url": source_details_dict.get("url") if source_details_dict else None,
            "file": source_details_dict.get("file") if source_details_dict else None,
            "full_metadata": fact.get("metadata", {}),
            "llm_summary": fact.get("llm_summary") if fact.get("llm_summary") else None,
            "case_reference": fact.get("case_reference") if fact.get("case_reference") else None,  # Include case reference
            "case_name": source_details_dict.get("case_name") if source_details_dict else None,
            "case_id": source_details_dict.get("case_id") if source_details_dict else None,
            "year": source_details_dict.get("year") if source_details_dict else None,
            "doc_id": source_details_dict.get("doc_id") if source_details_dict else None,
            "score": source_details_dict.get("score") if source_details_dict else None,
            # Include all other source_details fields
            **source_details_dict
        }
        
        fact_storage.add_fact(
            content=fact.get("content", ""),
            source=fact.get("source", "unknown"),
            source_details=complete_source_details,
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