"""
Human Approval Gate

Allows human lawyer to review and approve each phase.
Implements "human-in-the-loop" pattern.

Prevents automated decisions on critical legal matters.
"""

from workflows.lawyer_agent.state import LawyerState
import json


def _default_restart_for_phase(phase: str) -> str:
    mapping = {
        "facts": "fact_gathering",
        "analysis": "legal_analysis",
        "prediction": "prediction",
        "draft": "drafting",
    }
    return mapping.get(phase, "fact_gathering")


def human_approval_node(state: LawyerState, phase: str, llm=None, embedding_model=None) -> LawyerState:
    """
    Gate: Human review of completed phase.
    
    Inputs:
        - phase: Which phase to review ("facts", "analysis", "prediction", "draft")
        - state: Complete state with all previous outputs
    
    Outputs:
        - approved_phase: Which phase was approved
        - user_feedback: Any feedback from reviewer
    
    Options:
        - "approve": Continue to next phase
        - "revise": Request revision (would trigger phase repeat)
        - "stop": Stop workflow
    
    Philosophy:
        ✔ Lawyer has final say
        ✔ No auto-submission
        ✔ Feedback is captured
        ✔ Session is audited
    """
    
    print(f"\n🧑‍⚖️  HUMAN REVIEW GATE: {phase.upper()}")
    print(f"   {'=' * 50}")
    
    # Display current phase output
    if phase == "facts":
        print("\n📋 Facts Retrieved:")
        for i, fact in enumerate(state.get("facts", [])[:3], 1):
            print(f"   {i}. {fact.get('content', '')[:100]}...")
    
    elif phase == "analysis":
        print("\n⚖️  Analysis Generated:")
        print(state.get("analysis", "")[:300] + "...")
    
    elif phase == "prediction":
        print("\n🔮 Prediction:")
        print(state.get("prediction", "")[:300] + "...")
    
    elif phase == "draft":
        print("\n📄 Draft Document:")
        print(state.get("draft", "")[:300] + "...")
    
    print(f"\n   {'=' * 50}")
    
    # Get decision
    decision = input("\n👨‍⚖️  Your decision [approve/revise/stop]: ").strip().lower()
    
    if decision == "approve":
        # Clear any prior revise action when user approves
        if "revise_action" in state:
            state.pop("revise_action", None)
        state["approved_phase"] = phase
        
        # CRITICAL: If approving facts, lock them to prevent re-retrieval
        if phase == "facts":
            fact_storage = state.get("fact_storage")
            if fact_storage:
                # Approve any pending facts as part of the human "approve" action,
                # then lock approved facts so downstream phases won't re-run retrieval.
                pending = fact_storage.get_pending_facts()
                for f in pending:
                    fact_storage.approve_fact(f["id"])

                # Lock approved facts
                locked_facts = fact_storage.lock_approved_facts()
                state["facts_approved_and_locked"] = True
                state["approved_facts_count"] = len(locked_facts)
                print(f"   🔒 {len(locked_facts)} facts approved, locked and frozen for analysis phase.\n")
        
        print(f"   ✅ Phase '{phase}' approved. Continuing...\n")
        return state
    
    elif decision == "revise":
        feedback = input("   Feedback for revision: ")
        state["user_feedback"] = feedback
        print(f"   ⚠️  Phase will be revised with feedback: {feedback}\n")

        # Try to interpret feedback using LLM to produce a refined query
        # and a restart point in the graph. If no LLM provided, fallback
        # to restarting the corresponding phase and use the original
        # question + feedback as the refined query.
        refined_query = None
        restart_from = _default_restart_for_phase(phase)

        if llm is not None:
            prompt = (
                "You are an assistant that converts human reviewer feedback into a concise "
                "search query and recommends where the workflow should restart. "
                "Output strict JSON with keys: restart_from, refined_query.\n\n"
                f"Original question: {state.get('question','')}\n"
                f"Reviewer feedback: {feedback}\n\n"
                "Respond with JSON only. Example: {\"restart_from\": \"fact_gathering\", \"refined_query\": \"search terms...\"}"
            )

            try:
                resp = llm.generate(prompt, temperature=0.0, max_tokens=200)
                # Try to parse JSON from response
                parsed = None
                try:
                    parsed = json.loads(resp)
                except Exception:
                    # Attempt to extract JSON substring
                    start = resp.find('{')
                    end = resp.rfind('}')
                    if start != -1 and end != -1:
                        try:
                            parsed = json.loads(resp[start:end+1])
                        except Exception:
                            parsed = None

                if isinstance(parsed, dict):
                    restart_from = parsed.get('restart_from', restart_from)
                    refined_query = parsed.get('refined_query')
                else:
                    refined_query = (state.get('question','') + ' ' + feedback).strip()

            except Exception:
                refined_query = (state.get('question','') + ' ' + feedback).strip()
        else:
            refined_query = (state.get('question','') + ' ' + feedback).strip()

        # Parse refined query to extract year constraints (if any)
        # e.g., "right to privacy 2014 2018" → years=[2014, 2018]
        years = []
        if refined_query:
            import re
            year_matches = re.findall(r'\b(\d{4})\b', refined_query)
            years = sorted(list(set([int(m) for m in year_matches if 1900 <= int(m) <= 2100])))
        
        state['revise_action'] = {
            'restart_from': restart_from,
            'refined_query': refined_query,
            'constraint_years': years
        }

        return state
    
    elif decision == "stop":
        print("   ⛔ Workflow stopped by user.\n")
        raise KeyboardInterrupt("User stopped workflow at phase: " + phase)
    
    else:
        print("   ⚠️  Invalid input. Defaulting to 'approve'.")
        if "revise_action" in state:
            state.pop("revise_action", None)
        state["approved_phase"] = phase
        return state
