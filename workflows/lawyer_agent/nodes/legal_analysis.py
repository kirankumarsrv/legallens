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
    
    import traceback
    
    print("\n⚖️  PHASE 2: LEGAL ANALYSIS")
    print("   (Using Approved Facts → Precedent Search → Reasoning)\n")
    
    try:
        # Get tools available to LLM (for multilingual support)
        tools = get_all_lawyer_agent_tools()
        if tools:
            print(f"   📦 Tools available: {', '.join([t.name for t in tools])}")
    except Exception as e:
        print(f"   ❌ ERROR getting tools: {e}")
        traceback.print_exc()
        tools = []
    
    # CRITICAL: Get APPROVED & LOCKED facts from Phase 1
    # DO NOT re-retrieve statutes - use what was already approved
    try:
        fact_storage = state.get("fact_storage")
        print(f"   ✓ fact_storage retrieved: {fact_storage is not None}")
        
        if fact_storage and state.get("facts_approved_and_locked"):
            # Facts were approved and locked - use them
            statutes = fact_storage.get_approved_facts()
            print(f"   🔒 Using {len(statutes)} approved & locked statute facts from Phase 1")
        else:
            # Fallback: if no fact storage, use facts_raw from state
            # This shouldn't happen in normal flow but provides safety
            statutes = state.get("facts", [])
            print(f"   ⚠️  No locked facts found. Using {len(statutes)} facts from state (SHOULD NOT HAPPEN)")
    except Exception as e:
        print(f"   ❌ ERROR extracting facts: {e}")
        traceback.print_exc()
        statutes = []
    
    # Stage 2: NO PRECEDENT RETRIEVAL IN WORKFLOW 2
    # Workflow 2 only uses locked facts to generate arguments via LLM
    # No additional retrieval should happen here
    print("   🚫 Skipping precedent retrieval (Workflow 2: Argument Generation only)")
    precedents = []
    print(f"   📚 Using 0 precedent cases (arguments based on locked facts only)")
    
    # Stage 3: LLM reasoning
    # Build statute text from approved facts
    statute_text_parts = []
    try:
        for s in statutes[:3]:
            if s is None:
                continue
            if isinstance(s, dict):
                # Format 1: Dictionary from fact_storage
                statute_text_parts.append(f"[{s.get('source', 'Statute')}] {s.get('content', '')}")
            else:
                # Format 2: Raw string from facts
                statute_text_parts.append(f"[Statute] {str(s)[:200]}")
    except Exception as e:
        print(f"   ⚠️  Error building statute text: {e}")
    
    statute_text = "\n\n".join(statute_text_parts)
    
    precedent_text = ""
    try:
        precedent_text = "\n\n".join([f"[Case] {p.get('content', str(p))[:200]}..." for p in precedents[:2] if p])
    except Exception as e:
        print(f"   ⚠️  Error building precedent text: {e}")
    
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
    
    # Call LLM with tools - use high max_tokens for complete legal analysis
    try:
        analysis = llm.generate(prompt, max_tokens=4096, tools=tools, tool_choice="auto") if tools else llm.generate(prompt, max_tokens=4096)
    except TypeError:
        # Fallback for LLM implementations that don't support tools parameter
        analysis = llm.generate(prompt, max_tokens=4096)
    
    # Update state
    state["analysis"] = analysis
    state["statutes"] = statutes
    state["precedents"] = precedents

    # Ensure reasoning_trace exists
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []

    # Create ArgumentStorage and extract candidate arguments from analysis
    arg_store: ArgumentStorage = state.get("argument_storage") or ArgumentStorage()
    
    # Clear any existing pending arguments to avoid duplicates when re-running
    cleared_count = arg_store.clear_pending_arguments()
    if cleared_count > 0:
        print(f"   🗑️  Cleared {cleared_count} pending arguments from previous run")

    # Extract PRO-ARGUMENTS section from the analysis text
    analysis_text = analysis if isinstance(analysis, str) else str(analysis)
    pro_args = []
    
    # Get fact IDs from locked facts to link to arguments
    fact_ids = []
    if fact_storage:
        fact_ids = [fact.get('id') for fact in fact_storage.get_approved_facts() if fact.get('id')]
    
    try:
        lower = analysis_text.lower()
        start_idx = lower.find("pro-arguments")
        if start_idx == -1:
            start_idx = lower.find("pro arguments")
        if start_idx != -1:
            # find end (counter-arguments or next section)
            end_idx = lower.find("counter-arguments", start_idx)
            if end_idx == -1:
                end_idx = lower.find("3.", start_idx)
            section = analysis_text[start_idx:end_idx if end_idx != -1 else None]
            # split by numbered items (1., 2., 3.)
            import re
            items = re.split(r'\n\s*\d+\.\s+', section)
            for item in items[1:][:3]:  # Skip first empty split, take max 3 arguments
                item = item.strip()
                if len(item) > 30:  # Filter out headers
                    pro_args.append(item)
    except Exception as e:
        print(f"   ⚠️  Error extracting arguments: {e}")
        pro_args = []

    # Add extracted arguments with fact linking
    for a in pro_args:
        arg_store.add_argument(content=a, legal_basis="", fact_ids=fact_ids)
    
    print(f"   ✅ Generated {len(pro_args)} arguments linked to {len(fact_ids)} facts")

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
