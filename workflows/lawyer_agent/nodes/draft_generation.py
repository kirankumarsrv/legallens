"""
Phase 4: Draft Generation Node

Generates a structured legal document (draft) from the analysis, arguments, and prediction.
This is the final deliverable that combines all phases into a polished legal argument/memo.

Outputs:
  - draft: Comprehensive legal document with sections:
    - Executive Summary
    - Facts of the Case
    - Legal Question
    - Applicable Law & Precedent
    - Arguments (Pro & Counter)
    - Risk Assessment
    - Prediction & Recommendation
    - Supporting Statutes/Cases
"""

from workflows.lawyer_agent.state import LawyerState


def draft_generation_node(state: LawyerState, llm) -> LawyerState:
    """
    Phase 4: Generate a comprehensive legal draft/memorandum.
    
    Inputs from state:
        - question: Original legal question
        - analysis: Structured legal analysis from Phase 2
        - prediction: Strategic assessment from Phase 3
        - facts (from fact_storage): Approved & locked facts
        - argument_storage: Generated arguments from Phase 2
        - statutes: Statute references used
        - precedents: Case law references
    
    Output:
        - draft: Formatted legal memorandum
    """
    
    print("\n📄 PHASE 4: DRAFT GENERATION")
    print("   (Creating comprehensive legal document)\n")
    
    # Extract key information from state
    question = state.get("question", "")
    analysis = state.get("analysis", "")
    prediction = state.get("prediction", "")
    
    # Extract approved facts and arguments
    facts_text = ""
    try:
        fact_storage = state.get("fact_storage")
        if fact_storage:
            approved_facts = fact_storage.get_approved_facts()
            if approved_facts:
                facts_text = "\n".join([
                    f"• {f.get('content', '')[:200]}"
                    for f in approved_facts[:10]
                ])
    except Exception:
        pass
    
    arguments_text = ""
    try:
        arg_storage = state.get("argument_storage")
        if arg_storage:
            approved_args = arg_storage.get_approved_arguments() if hasattr(arg_storage, 'get_approved_arguments') else []
            if approved_args:
                arguments_text = "\n".join([
                    f"• {a.get('content', '')[:150]}"
                    for a in approved_args[:5]
                ])
            else:
                # Fallback: all arguments if approval method not available
                all_args = getattr(arg_storage, 'arguments', {}).values() if hasattr(arg_storage, 'arguments') else []
                if all_args:
                    arguments_text = "\n".join([
                        f"• {a.get('content', '')[:150]}"
                        for a in list(all_args)[:5]
                    ])
    except Exception:
        pass
    
    # Generate draft via LLM
    prompt = f"""You are a legal document drafter. Create a comprehensive legal memorandum based on the following information.

**LEGAL QUESTION:**
{question}

**FACTS OF THE CASE:**
{facts_text if facts_text else "(No specific facts provided)"}

**LEGAL ANALYSIS:**
{analysis[:800] if analysis else "(No analysis provided)"}

**ARGUMENTS:**
{arguments_text if arguments_text else "(No arguments provided)"}

**STRATEGIC ASSESSMENT:**
{prediction[:400] if prediction else "(No prediction provided)"}

---

**TASK:** Generate a structured legal memorandum with the following sections:

1. **EXECUTIVE SUMMARY** (100-150 words)
   - Concise overview of the case and recommendation

2. **STATEMENT OF FACTS**
   - Key facts extracted from the case evidence

3. **LEGAL QUESTION**
   - Clear statement of what the law requires or permits

4. **APPLICABLE LAW**
   - Relevant statutes, regulations, and case precedent
   - How the law applies to these facts

5. **ARGUMENTS**
   - Arguments supporting our position
   - Counter-arguments and how to address them

6. **RISK ASSESSMENT**
   - Main legal risks and exposure
   - Mitigation strategies

7. **CONCLUSION & RECOMMENDATION**
   - Overall assessment (STRONG/MODERATE/WEAK case)
   - Recommended strategy
   - Next steps

---

**FORMAT:**
- Use professional legal language
- Cite statutes and cases where mentioned
- Use clear section headers
- Keep total length 2000-3000 words
- Maintain neutral, objective tone
- Include specific numbers/dates where available

Generate the complete memorandum now:
"""

    try:
        draft = llm.generate(prompt)
        print("   ✅ Draft generated successfully")
    except Exception as e:
        print(f"   ⚠️  Draft generation failed: {e}")
        draft = f"[Draft generation failed]\n\nLegal Question: {question}\n\nAnalysis Summary: {analysis[:500]}"
    
    # Update state
    state["draft"] = draft
    
    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    state["reasoning_trace"].append("PHASE 4: Legal draft/memorandum generated")
    
    return state
