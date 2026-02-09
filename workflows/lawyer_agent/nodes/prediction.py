"""
Phase 3: Prediction Node with backtrack/history support

This node generates outcome predictions based on existing arguments ONLY.
NO retrieval is performed - it uses the arguments already generated.

Features:
- Keeps a `prediction_history` list in `state` when `backtrack_enabled` is True
- Detects edits to facts/arguments via state flags and forces recomputation
- Allows restoring a prior prediction via `restore_prediction_index` in state

Outputs appended to state:
- `prediction` (current prediction text)
- `prediction_confidence` (0-1 placeholder)
- `prediction_history` (list of prior predictions)
"""

from datetime import datetime, timezone
from copy import deepcopy

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
            "analysis_snapshot": state.get("analysis", ""),
            "facts_snapshot": deepcopy(state.get("facts_approved_and_locked", [])),
            "arguments_snapshot": deepcopy(state.get("argument_storage", {}).get_all_arguments() if state.get("argument_storage") else []),
        }
        state["prediction_history"].append(hist_item)
        # Trim history
        if len(state["prediction_history"]) > max_history:
            state["prediction_history"] = state["prediction_history"][-max_history:]

    # Workflow 3: NO RETRIEVAL - Use existing arguments only
    # Get arguments from argument_storage
    argument_storage = state.get('argument_storage')
    
    if not argument_storage:
        state["prediction"] = "No arguments available. Please generate arguments first (Workflow 2)."
        state["prediction_confidence"] = 0.0
        state["reasoning_trace"].append(
            "PHASE 3: No arguments available; prediction skipped."
        )
        return state
    
    arguments = argument_storage.get_all_arguments()
    
    if not arguments:
        state["prediction"] = "No arguments found. Please run argument generation first (Workflow 2)."
        state["prediction_confidence"] = 0.0
        state["reasoning_trace"].append(
            "PHASE 3: No arguments found; prediction skipped."
        )
        return state
    
    print(f"   📊 Using {len(arguments)} arguments to generate prediction (NO retrieval)")

    # Build arguments text for the prompt
    arguments_text = "\n\n".join([
        f"**Argument {i+1}:**\n{arg.get('text', arg.get('content', str(arg)))}"
        for i, arg in enumerate(arguments[:10])  # Limit to top 10 arguments
    ])

    # LLM-driven prediction based on arguments only
    prompt = f"""You are a litigation strategist. Assess the strength of this legal position based on the arguments provided.

**LEGAL QUESTION:**
{state.get('question')}

**ARGUMENTS DEVELOPED:**
{arguments_text}

Based ONLY on the arguments above, provide a strategic assessment including:
1. **Strength Rating**: STRONG/MODERATE/WEAK
2. **Probability Estimate**: 0-100% chance of success
3. **Confidence Level**: LOW/MEDIUM/HIGH
4. **Key Recommendations**: Specific action items

Be conservative and cite specific arguments when applicable.
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
    state["prediction_confidence"] = 0.7  # Placeholder - better parsing can set this

    # Clear edit flags now that prediction has been regenerated
    state["facts_edited"] = False
    state["arguments_edited"] = False

    # Audit trail
    state["reasoning_trace"].append(
        f"PHASE 3: Generated outcome prediction based on {len(arguments)} arguments (NO retrieval)."
    )

    return state
