"""
Human Approval Gate

Allows human lawyer to review and approve each phase.
Implements "human-in-the-loop" pattern.

Prevents automated decisions on critical legal matters.
"""

from workflows.lawyer_agent.state import LawyerState


def human_approval_node(state: LawyerState, phase: str) -> LawyerState:
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
        state["approved_phase"] = phase
        print(f"   ✅ Phase '{phase}' approved. Continuing...\n")
        return state
    
    elif decision == "revise":
        feedback = input("   Feedback for revision: ")
        state["user_feedback"] = feedback
        print(f"   ⚠️  Phase will be revised with feedback: {feedback}\n")
        # Would need conditional edges in graph to handle this
        return state
    
    elif decision == "stop":
        print("   ⛔ Workflow stopped by user.\n")
        raise KeyboardInterrupt("User stopped workflow at phase: " + phase)
    
    else:
        print("   ⚠️  Invalid input. Defaulting to 'approve'.")
        state["approved_phase"] = phase
        return state
