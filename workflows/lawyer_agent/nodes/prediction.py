"""
Phase 3: Prediction Node

Retrieves similar cases using METADATA-FIRST approach.
FAISS-based pattern matching with targeted year selection.

Outputs: Probability of favorable/unfavorable outcome.
"""

from workflows.lawyer_agent.retrieval.precedents import retrieve_precedents
from workflows.lawyer_agent.state import LawyerState


def prediction_node(state: LawyerState, faiss_store, llm, embedding_model=None) -> LawyerState:
    """
    Third phase: Outcome prediction using METADATA-FIRST approach.
    
    Inputs from state:
        - analysis: Legal analysis from Phase 2
        - facts: Facts from Phase 1
    
    Outputs to state:
        - prediction: Outcome probability estimate
        - similar_cases: Cases used for prediction
        - prediction_confidence: Confidence score (0-1)
    
    Philosophy:
        ✔ METADATA-FIRST routing
        ✔ PATTERN MATCHING from relevant years only
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
    
    prompt = f"""Based on these similar cases:

{cases_text}

Question:
{state['question']}

Estimate:
1. Probability of favorable outcome (0-100%)
2. Confidence level (low/medium/high)
3. Key factors affecting outcome
4. Reasoning (which cases are most similar and why)

Be conservative. Acknowledge uncertainty."""

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
    
    if not similar_cases:
        state["prediction"] = "Insufficient case law for prediction."
        state["similar_cases"] = []
        state["prediction_confidence"] = 0.0
        return state
    
    # LLM prediction
    cases_text = "\n\n".join([f"Case: {c['content'][:150]}..." for c in similar_cases[:5]])
    
    prompt = f"""Based on these similar cases:

{cases_text}

Question:
{state['question']}

Estimate:
1. Probability of favorable outcome (0-100%)
2. Confidence level (low/medium/high)
3. Key factors affecting outcome
4. Reasoning (which cases are most similar and why)

Be conservative. Acknowledge uncertainty."""

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
