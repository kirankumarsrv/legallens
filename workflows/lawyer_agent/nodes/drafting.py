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
    
    prompt = f"""You are an expert legal drafter. Compose a professional, court-ready legal document.

**APPROVED LEGAL ANALYSIS:**
{analysis_text}

**SUPPORTING STATUTES & CASE LAW TO CITE:**
{citations_text}

**AVAILABLE TEMPLATE/FORMAT GUIDANCE:**
{template_text}

**TASK: Draft a formal legal petition/brief with the following structure and requirements:**

**SECTION 1: INTRODUCTION & RELIEF SOUGHT**
- Brief statement of what relief is being requested
- Cite the constitutional or statutory basis for the petition (e.g., Article 226, Article 32)
- Identify the parties (Petitioner vs. Respondent)

**SECTION 2: STATEMENT OF FACTS**
- Present facts in clear, chronological order
- Focus on facts that are legally relevant
- Be concise but complete; facts should support the legal arguments
- Use neutral, professional language (no emotional language)

**SECTION 3: LEGAL ARGUMENTS**
- Build arguments using:
  * The applicable statutes (cite sections: e.g., "Article 21 of the Constitution protects...")
  * Supporting precedent cases (cite names and years: e.g., "In K.S. Puttaswamy v. UoI (2017)...")
  * How the law applies to our facts
- Address counter-arguments (even if briefly) to show you anticipated them
- Use formal legal language and proper sentence structure

**SECTION 4: CONCLUSION & RELIEF**
- Summarize the strongest legal points
- Clearly state what relief/remedy is sought
- End with a formal closing (e.g., "WHEREFORE, the Petitioner prays that...")

**CITATION REQUIREMENTS:**
- Cite statutes in brackets: [Article 21, Constitution] or [IPC Section 377]
- Cite cases in parentheses: (K.S. Puttaswamy v. Union of India, 2017)
- Every legal claim must have a citation
- Use consistent citation format throughout

**FORMATTING REQUIREMENTS:**
1. Professional legal document format
2. Clear section headings
3. Numbered paragraphs for easy reference
4. Proper margins and spacing
5. All citations clearly marked
6. Length: 3-5 pages (court-appropriate)

**LANGUAGE & TONE:**
- Formal, professional legal language
- Avoid emotional or colloquial language
- Use active voice, clear sentence structure
- Be persuasive but not argumentative
- Respect for court authority and procedures

**QUALITY CHECKS:**
- Is every legal argument supported by a statute or case?
- Are all citations formatted consistently?
- Is the document logically structured and easy to follow?
- Would a lawyer feel confident filing this in court?

Draft the document now with full compliance to all requirements above."""

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
