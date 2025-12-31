"""
Phase 3: Prediction Node with backtrack/history support

This node performs the same YEARWISE FAISS-based precedent retrieval
and LLM-driven strategic assessment as before, but also:
- Keeps a `prediction_history` list in `state` when `backtrack_enabled` is True
- Detects edits to facts/arguments via state flags and forces recomputation
- Allows restoring a prior prediction via `restore_prediction_index` in state

Outputs appended to state:
- `prediction` (current prediction text)
- `prediction_confidence` (0-1 placeholder)
- `similar_cases` (cases used for the current prediction)
- `prediction_history` (list of prior predictions)
"""

from datetime import datetime, timezone
from copy import deepcopy

from workflows.lawyer_agent.retrieval.precedents import retrieve_precedents
from workflows.lawyer_agent.state import LawyerState


def _ensure_history(state: LawyerState):
    if "prediction_history" not in state:
        state["prediction_history"] = []


def prediction_node(
    state: LawyerState,
    faiss_store,
    llm,
    embedding_model=None,
    backtrack_enabled: bool = True,
    max_history: int = 10,
):
    """Outcome prediction with optional backtrack/history.

    Triggers a recompute if one of these flags is present and truthy in state:
      - `recompute_prediction`
      - `prediction_force_recompute`
      - `facts_edited`
      - `arguments_edited`

    To restore a previous prediction, set `restore_prediction_index` to an
    integer index (0 = oldest) and the node will replace the current
    prediction with that history entry.
    """

    print("\n🔮 PHASE 3: OUTCOME PREDICTION (with backtrack support)")

    # Initialize history container
    _ensure_history(state)

    # Handle explicit restore from history
    if "restore_prediction_index" in state:
        idx = state.pop("restore_prediction_index")
        try:
            item = state["prediction_history"][int(idx)]
            state["prediction"] = item.get("prediction")
            state["similar_cases"] = deepcopy(item.get("similar_cases", []))
            state["prediction_confidence"] = item.get("prediction_confidence", 0.0)
            state["reasoning_trace"].append(
                f"PHASE 3: Restored prediction from history index {idx}."
            )
        except Exception:
            state["reasoning_trace"].append(
                f"PHASE 3: Failed to restore prediction at index {idx}."
            )
        return state

    # Determine whether to recompute
    force_recompute = bool(
        state.pop("recompute_prediction", False)
        or state.pop("prediction_force_recompute", False)
        or state.get("facts_edited", False)
        or state.get("arguments_edited", False)
    )

    # If a prediction already exists and no force recompute requested, skip work
    if state.get("prediction") and not force_recompute:
        print("→ Prediction already exists and no recompute requested; skipping.")
        return state

    # If we will recompute and backtrack is enabled, save current prediction
    if force_recompute and backtrack_enabled and state.get("prediction"):
        hist_item = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prediction": state.get("prediction"),
            "prediction_confidence": state.get("prediction_confidence", 0.0),
            "similar_cases": deepcopy(state.get("similar_cases", [])),
            "analysis_snapshot": state.get("analysis", ""),
            "facts_snapshot": deepcopy(state.get("facts_approved_and_locked", [])),
        }
        state["prediction_history"].append(hist_item)
        # Trim history
        if len(state["prediction_history"]) > max_history:
            state["prediction_history"] = state["prediction_history"][-max_history:]

    # Retrieve similar cases using METADATA-FIRST approach
    query_text = f"{state.get('analysis','')[:300]} { ' '.join(state.get('facts_raw',[])[:1]) }"
    similar_cases = retrieve_precedents(
        query=query_text,
        faiss_store=faiss_store,
        embedding_model=embedding_model,
        k=7,
    )

    if not similar_cases:
        state["prediction"] = "Insufficient case law for prediction."
        state["similar_cases"] = []
        state["prediction_confidence"] = 0.0
        state["reasoning_trace"].append(
            "PHASE 3: No similar cases found; prediction skipped."
        )
        return state

    # LLM-driven prediction
    cases_text = "\n\n".join([f"Case: {c.get('content','')[:150]}..." for c in similar_cases[:5]])

    prompt = f"""You are a litigation strategist. Assess the strength of this legal position based on precedent patterns.

**LEGAL QUESTION:**
{state.get('question')}

**CASE ANALYSIS:**
{state.get('analysis','')[:500]}

**SIMILAR PRECEDENT CASES:**
{cases_text}

Provide a strategic assessment (rating: STRONG/MODERATE/WEAK), a probability estimate (0-100%), a confidence level (LOW/MEDIUM/HIGH), and key recommendations.
Be conservative and cite specific cases when applicable.
"""

    # Use LLM safely (some LLMs expose `generate`, others `call` or `complete`)
    try:
        prediction = llm.generate(prompt)
    except Exception:
        try:
            prediction = llm.call(prompt)
        except Exception:
            prediction = "(LLM unavailable) Prediction could not be generated."

    # Update state with new prediction
    state["prediction"] = prediction
    state["similar_cases"] = similar_cases
    state["prediction_confidence"] = 0.7  # Placeholder - better parsing can set this

    # Clear edit flags now that prediction has been regenerated
    state["facts_edited"] = False
    state["arguments_edited"] = False

    # Audit trail
    state["reasoning_trace"].append(
        f"PHASE 3: Retrieved {len(similar_cases)} similar cases. Outcome prediction generated."
    )

    return state
