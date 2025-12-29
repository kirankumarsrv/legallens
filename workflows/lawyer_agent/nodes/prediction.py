"""
Phase 3: Prediction Node

Retrieves similar cases using yearwise FAISS scanning.
Direct year scanning from 1950..2025 with fallback to global FAISS.
FAISS-based pattern matching for outcome prediction.

Outputs: Probability of favorable/unfavorable outcome.
"""

from workflows.lawyer_agent.retrieval.precedents import retrieve_precedents
from workflows.lawyer_agent.state import LawyerState


def prediction_node(state: LawyerState, faiss_store, llm, embedding_model=None) -> LawyerState:
    """
    Third phase: Outcome prediction using yearwise FAISS scanning.
    
    Inputs from state:
        - analysis: Legal analysis from Phase 2
        - facts: Facts from Phase 1
    
    Outputs to state:
        - prediction: Outcome probability estimate
        - similar_cases: Cases used for prediction
        - prediction_confidence: Confidence score (0-1)
    
    Philosophy:
        ✔ YEARWISE FAISS scanning (1950..2025)
        ✔ PATTERN MATCHING from all available years
        ✔ Historical trends, not new arguments
        ✔ Probabilistic (not deterministic)
        ✔ For decision-making, not persuasion
    """
    
    print("\n🔮 PHASE 3: OUTCOME PREDICTION")
    print("   (Metadata → Targeted FAISS → Patterns → Probability)\n")
    
    # Retrieve similar cases using METADATA-FIRST approach
    similar_cases = retrieve_precedents(
        query=f"{state['analysis'][:300]} {' '.join(state['facts_raw'][:1])}",
        faiss_store=faiss_store,
        embedding_model=embedding_model,
        k=7
    )
    
    if not similar_cases:
        state["prediction"] = "Insufficient case law for prediction."
        state["similar_cases"] = []
        state["prediction_confidence"] = 0.0
        return state
    
    # LLM prediction
    cases_text = "\n\n".join([f"Case: {c['content'][:150]}..." for c in similar_cases[:5]])
    
    prompt = f"""You are a litigation strategist. Assess the strength of this legal position based on precedent patterns.

**LEGAL QUESTION:**
{state['question']}

**CASE ANALYSIS:**
{state['analysis'][:500]}

**SIMILAR PRECEDENT CASES:**
{cases_text}

**TASK: Provide a strategic case assessment with the following sections:**

1. **CASE STRENGTH ASSESSMENT** (Overall likelihood of favorable outcome)
   - Rate: STRONG / MODERATE / WEAK
   - Explain your rating based on the facts and applicable law
   - Which elements of our case are strongest? Which are weakest?

2. **FAVORABLE PRECEDENTS** (Cases that support our position)
   - List the precedent cases that help us
   - For each case: What facts were similar? What was the outcome? Why is it favorable?
   - How do these cases strengthen our arguments?

3. **UNFAVORABLE PRECEDENTS** (Cases that could hurt our position)
   - List the precedent cases that could harm us
   - For each case: What facts were similar? What was the outcome? Why is it unfavorable?
   - Can we distinguish ourselves from these cases? How?

4. **PROBABILITY ESTIMATE** (Likelihood of favorable outcome)
   - Estimate the probability: __% (0-100%)
   - Base this on:
     * How many favorable vs. unfavorable precedents?
     * Strength of the facts in our favor?
     * How do courts typically rule on this issue?

5. **CONFIDENCE LEVEL**
   - Rate: LOW / MEDIUM / HIGH
   - Explain: Is the prediction confident based on clear precedent, or is there ambiguity?

6. **KEY RISK FACTORS** (What could go wrong?)
   - List 2-3 major legal or factual risks
   - For each risk: Why is it a concern? What's the potential impact on the case?
   - How can we mitigate or address each risk?

7. **STRATEGIC RECOMMENDATIONS**
   - Based on the assessment, what is the best strategic path forward?
   - Should we prioritize settlement, negotiation, or litigation?
   - What arguments are most likely to succeed with a court?

**IMPORTANT:**
- If there is insufficient precedent, say so explicitly: "Prediction confidence is LOW due to limited case law."
- Be conservative: Acknowledge uncertainty and avoid overconfidence
- Cite specific cases by name and year to support each assessment

**TONE:** Strategic, analytical, honest about risks."""

    prediction = llm.generate(prompt)
    
    # Update state
    state["prediction"] = prediction
    state["similar_cases"] = similar_cases
    state["prediction_confidence"] = 0.7  # Placeholder - would parse from LLM output
    
    # Audit trail
    state["reasoning_trace"].append(
        f"PHASE 3: Retrieved {len(similar_cases)} similar cases. Outcome prediction generated."
    )
    
    return state
