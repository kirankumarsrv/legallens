"""
Phase 2: Legal Analysis Node

Retrieves statutes + precedents.
Performs structured legal reasoning.

Outputs arguments, counter-arguments, statutory interpretation.
"""

from workflows.lawyer_agent.retrieval.statutes import retrieve_statutes
from workflows.lawyer_agent.retrieval.precedents import retrieve_precedents
from workflows.lawyer_agent.state import LawyerState


def legal_analysis_node(state: LawyerState, chroma_stores: dict, embedding_model, faiss_store, llm) -> LawyerState:
    """
    Second phase: Legal analysis and reasoning.
    
    Inputs from state:
        - question: Original question
        - facts: Statute sections from Phase 1
    
    Outputs to state:
        - analysis: Structured legal reasoning
        - statutes: Statute references
        - precedents: Case law references
    
    Philosophy:
        ✔ Statutes FIRST (binding authority)
        ✔ Precedents AFTER (persuasive authority)
        ✔ Structured reasoning (arguments + counter-arguments)
        ✔ Explainable (can show why each source was used)
    """
    
    print("\n⚖️  PHASE 2: LEGAL ANALYSIS")
    print("   (Statutes → Precedents → Reasoning)\n")
    
    # Stage 1: Retrieve statutes
    statutes = retrieve_statutes(
        query=state["question"],
        chroma_stores=chroma_stores,
        embedding_model=embedding_model,
        k=6
    )
    
    # Stage 2: Retrieve precedents
    combined_query = f"{state['question']} {' '.join(state['facts_raw'][:2])}"
    precedents = retrieve_precedents(
        query=combined_query,
        faiss_store=faiss_store,
        embedding_model=embedding_model,
        k=5
    )
    
    # Stage 3: LLM reasoning
    statute_text = "\n\n".join([f"[{s['source']}] {s['content']}" for s in statutes[:3]])
    precedent_text = "\n\n".join([f"[Case] {p['content'][:200]}..." for p in precedents[:2]])
    
    prompt = f"""You are a legal expert. Perform structured legal analysis.

Question:
{state['question']}

Applicable Statutes:
{statute_text}

Relevant Precedents:
{precedent_text}

Provide:
1. Legal Position (what the law says)
2. Arguments (why it applies)
3. Counter-Arguments (possible objections)
4. Statutory Interpretation (how courts interpret it)
5. Conclusion (your expert opinion)

Be precise, cite sections, mention relevant cases."""

    analysis = llm.generate(prompt)
    
    # Update state
    state["analysis"] = analysis
    state["statutes"] = statutes
    state["precedents"] = precedents
    
    # Audit trail
    state["reasoning_trace"].append(
        f"PHASE 2: Retrieved {len(statutes)} statutes + {len(precedents)} precedents. LLM analysis generated."
    )
    
    return state
