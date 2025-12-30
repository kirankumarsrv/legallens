import os
import sys

# Ensure project root is on sys.path for test discovery
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from workflows.lawyer_agent.cli_fact_refiner import interactive_refiner


def test_non_interactive_approval():
    state = {}
    # Approve first, reject second, edit+approve third
    approvals = {
        0: "approve",
        1: "reject",
        2: ("edit", "Personal emails accessed revealing health information and spouse details."),
    }

    new_state = interactive_refiner(state, non_interactive=True, approvals=approvals)

    fs = new_state.get("fact_storage")
    stats = fs.get_summary_stats()

    assert stats["approved_facts"] == 2
    assert stats["rejected_facts"] == 1
    assert new_state.get("facts_approved_and_locked") is True
