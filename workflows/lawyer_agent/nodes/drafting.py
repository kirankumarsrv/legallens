"""
Phase 4: Drafting Node

Retrieves templates and citations.
Generates court-safe legal document.

Outputs: Formatted, cited legal brief.
"""

from workflows.lawyer_agent.retrieval.drafts import retrieve_drafts
from workflows.lawyer_agent.retrieval.precedents import retrieve_precedents
from workflows.lawyer_agent.state import LawyerState


def drafting_node(state: LawyerState, chroma_drafts, embedding_model, faiss_store, llm) -> LawyerState:
    """
    Fourth phase: Document drafting.
    
    Inputs from state:
        - analysis: Legal analysis from Phase 2
        - statutes: Statute sections
        - precedents: Case law
    
    Outputs to state:
        - draft: Final legal document
        - templates: Templates used
        - citations: Cases cited
    
    Philosophy:
        ✔ STRUCTURE from templates
        ✔ CONTENT from analysis
        ✔ CITATIONS from precedents
        ✔ LANGUAGE is formal and legal
    """
    
    print("\n✍️  PHASE 4: DRAFTING")
    print("   (Templates → Content → Citations → Document)\n")
    
    # Retrieve templates
    templates = retrieve_drafts(
        query=state["analysis"],
        chroma_store=chroma_drafts,
        embedding_model=embedding_model,
        k=3
    )
    
    # Retrieve citations
    citations = retrieve_precedents(
        query=state["analysis"],
        faiss_store=faiss_store,
        k=4
    )
    
    # LLM drafting
    template_text = "\n\n".join([f"[Template] {t['content'][:200]}..." for t in templates[:2]]) if templates else "Standard legal document format"
    citations_text = "\n\n".join([f"Citation: {c['content'][:100]}..." for c in citations[:3]]) if citations else "Reference cases as appropriate"
    analysis_text = state["analysis"][:500]
    
    prompt = f"""Draft a formal legal document.

Template Structure:
{template_text}

Analysis:
{analysis_text}

Citations:
{citations_text}

Requirements:
1. Professional legal language
2. Proper citations in brackets [citation]
3. Structured sections (Introduction, Facts, Legal Arguments, Conclusion)
4. Court-safe formatting
5. 2-3 pages maximum

Draft the document now."""

    draft = llm.generate(prompt)
    
    # Update state
    state["draft"] = draft
    state["templates"] = templates
    state["citations"] = citations
    
    # Audit trail
    state["reasoning_trace"].append(
        f"PHASE 4: Retrieved {len(templates)} templates + {len(citations)} citations. Document drafted."
    )
    
    return state
