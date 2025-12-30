"""
Phase 2: Legal Analysis Node

Retrieves statutes + precedents.
Performs structured legal reasoning with multilingual tool support.

Outputs arguments, counter-arguments, statutory interpretation.
Tools available: legal_translator, extract_legal_terms (LLM can call if needed)
"""

from workflows.lawyer_agent.retrieval.statutes import retrieve_statutes
from workflows.lawyer_agent.retrieval.precedents import retrieve_precedents
from workflows.lawyer_agent.tools import get_all_lawyer_agent_tools
from workflows.lawyer_agent.state import LawyerState
from modules.argument_storage import ArgumentStorage


def legal_analysis_node(state: LawyerState, chroma_stores: dict, embedding_model, faiss_store, llm) -> LawyerState:
    """
    Second phase: Legal analysis and reasoning.
    
    Inputs from state:
        - question: Original question
        - facts: Statute sections from Phase 1 (APPROVED & LOCKED)
    
    Outputs to state:
        - analysis: Structured legal reasoning
        - statutes: Statute references
        - precedents: Case law references
    
    Philosophy:
        ✔ Statutes FIRST (binding authority)
        ✔ Precedents AFTER (persuasive authority)
        ✔ Structured reasoning (arguments + counter-arguments)
        ✔ Explainable (can show why each source was used)
        ✔ NO RE-RETRIEVAL: Use approved facts from Phase 1, don't retrieve again
    """
    
    print("\n⚖️  PHASE 2: LEGAL ANALYSIS")
    print("   (Using Approved Facts → Precedent Search → Reasoning)\n")
    
    # Get tools available to LLM (for multilingual support)
    tools = get_all_lawyer_agent_tools()
    if tools:
        print(f"   📦 Tools available: {', '.join([t.name for t in tools])}")
    
    # CRITICAL: Get APPROVED & LOCKED facts from Phase 1
    # DO NOT re-retrieve statutes - use what was already approved
    fact_storage = state.get("fact_storage")
    if fact_storage and state.get("facts_approved_and_locked"):
        # Facts were approved and locked - use them
        statutes = fact_storage.get_approved_facts()
        print(f"   🔒 Using {len(statutes)} approved & locked statute facts from Phase 1")
    else:
        # Fallback: if no fact storage, use facts_raw from state
        # This shouldn't happen in normal flow but provides safety
        statutes = state.get("facts", [])
        print(f"   ⚠️  No locked facts found. Using {len(statutes)} facts from state (SHOULD NOT HAPPEN)")
    
    # Stage 2: Retrieve ONLY precedents (case law from yearwise FAISS)
    # This is NEW retrieval (not re-retrieval) - we're adding precedent cases
    combined_query = f"{state['question']} {' '.join(state['facts_raw'][:2])}"
    # If revise_action contains year constraints, pass them to precedent retrieval
    target_years = None
    if state.get('revise_action') and state['revise_action'].get('constraint_years'):
        target_years = state['revise_action'].get('constraint_years')

    precedents = retrieve_precedents(
        query=combined_query,
        faiss_store=faiss_store,
        embedding_model=embedding_model,
        k=5,
        target_years=target_years
    )
    
    print(f"   📚 Retrieved {len(precedents)} precedent cases for legal analysis")
    
    # Stage 3: LLM reasoning
    # Build statute text from approved facts
    statute_text_parts = []
    for s in statutes[:3]:
        if isinstance(s, dict):
            # Format 1: Dictionary from fact_storage
            statute_text_parts.append(f"[{s.get('source', 'Statute')}] {s.get('content', '')}")
        else:
            # Format 2: Raw string from facts
            statute_text_parts.append(f"[Statute] {str(s)[:200]}")
    statute_text = "\n\n".join(statute_text_parts)
    
    precedent_text = "\n\n".join([f"[Case] {p['content'][:200]}..." for p in precedents[:2]])
    
    prompt = f"""You are an expert legal analyst. Perform structured legal analysis combining statutory law with precedent.

**LEGAL QUESTION:**
{state['question']}

**APPLICABLE STATUTES & LEGAL RULES:**
{statute_text}

**RELEVANT PRECEDENT CASES:**
{precedent_text}

**TASK: Analyze and provide the following sections:**

1. **LEGAL POSITION** (What does the law say?)
   - State the relevant legal rules from the statutes
   - Explain who the law applies to and under what conditions
   - Cite specific statute sections

2. **PRO-ARGUMENTS** (Facts/law that SUPPORT our position)
   - List 2-3 strong arguments based on the facts and applicable statutes
   - For each argument, cite the supporting statute section or case
   - Explain why this argument is persuasive

3. **COUNTER-ARGUMENTS** (Potential weaknesses/opposing positions)
   - List 2-3 arguments that could be raised AGAINST our position
   - Explain why courts might find these persuasive
   - Identify how to address or mitigate these risks

4. **PRECEDENT ANALYSIS** (How have courts decided similar cases?)
   - Compare the facts of our case with the precedent cases
   - Which cases favor us? Why?
   - Which cases disfavor us? How can we distinguish them?
   - What interpretation have courts used consistently?

5. **STATUTORY INTERPRETATION** (How have courts read these laws?)
   - Explain how courts have historically interpreted the applicable statutes
   - Are there conflicting interpretations? Which is more favorable?
   - Any recent judicial trends?

6. **RISK ASSESSMENT & MITIGATION**
   - What are the main legal risks in our position?
   - How can we address these risks in our arguments?
   - Any conflicting laws we need to reconcile?

**FORMAT:**
- Be precise and cite statute sections (e.g., Article 21, IPC Section 377)
- Reference cases by name and year (e.g., K.S. Puttaswamy v. UoI, 2017)
- Use clear, structured sections as above
- Avoid speculation; base everything on the facts and law provided

**TONE:** Professional, neutral, analytical."""

    # Add language context if evidence is not in English
    if state.get("detected_language") and state["detected_language"] != "en":
        language_name = state.get("source_language_name", "Unknown")
        prompt += (f"\n\n**IMPORTANT NOTE:** The original evidence is in {language_name}. "
                   f"Tools are available if you need translation or term extraction for clarity.")
    
    # Call LLM with tools
    try:
        analysis = llm.generate(prompt, tools=tools, tool_choice="auto") if tools else llm.generate(prompt)
    except TypeError:
        # Fallback for LLM implementations that don't support tools parameter
        analysis = llm.generate(prompt)
    
    # Update state
    state["analysis"] = analysis
    state["statutes"] = statutes
    state["precedents"] = precedents

    # Ensure reasoning_trace exists
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []

    # Create ArgumentStorage and extract candidate arguments from analysis
    arg_store: ArgumentStorage = state.get("argument_storage") or ArgumentStorage()

    # Naive extraction: try to parse PRO-ARGUMENTS section from the analysis text
    analysis_text = analysis if isinstance(analysis, str) else str(analysis)
    pro_args = []
    try:
        lower = analysis_text.lower()
        start_idx = lower.find("pro-arguments")
        if start_idx == -1:
            start_idx = lower.find("pro arguments")
        if start_idx != -1:
            # find end (counter-arguments or next section)
            end_idx = lower.find("counter-arguments", start_idx)
            if end_idx == -1:
                # try numeric section marker
                end_idx = lower.find("3.", start_idx)
            section = analysis_text[start_idx:end_idx if end_idx != -1 else None]
            # split lines and pick bullets/lines
            for line in section.splitlines():
                line = line.strip().lstrip("-*")
                if not line:
                    continue
                # basic filter to avoid heading lines
                if len(line) > 20:
                    pro_args.append(line)
    except Exception:
        pro_args = []

    # If no pro_args extracted, create a fallback single argument from analysis summary
    if not pro_args:
        snippet = analysis_text[:400]
        pro_args = [f"Summary argument: {snippet}"]

    # Add up to 10 arguments into storage
    for a in pro_args[:10]:
        arg_store.add_argument(content=a, legal_basis="")

    state["argument_storage"] = arg_store
    
    # Mark facts as used in legal_analysis phase
    if fact_storage:
        for fact_id in fact_storage.approved_fact_ids:
            fact_storage.mark_fact_used_in_phase(fact_id, "legal_analysis")
    
    # Audit trail
    state["reasoning_trace"].append(
        f"PHASE 2: Used {len(statutes)} approved statute facts + retrieved {len(precedents)} precedent cases. LLM analysis generated."
    )
    
    return state
