from typing import Dict, Any, Optional

from modules.fact_storage import FactStorage


def interactive_refiner(state: Optional[Dict[str, Any]] = None, non_interactive: bool = False, approvals: Dict[int, Any] = None) -> Dict[str, Any]:
    """Simple CLI-like fact refiner for testing.

    Args:
        state: Existing LawyerState-like dict (may include 'fact_storage')
        non_interactive: If True, uses `approvals` mapping instead of input()
        approvals: Mapping index->action, where action is 'approve'|'reject'|'edit' or a tuple ('edit', new_text)

    Returns:
        Updated state with `fact_storage` and `facts_approved_and_locked` set.
    """
    state = state or {}

    if state.get("fact_storage") is None:
        state["fact_storage"] = FactStorage()

    fs: FactStorage = state["fact_storage"]

    # Seed sample facts if none present (helps tests)
    if not fs.get_all_facts():
        sample_facts = [
            {"content": "Employer installed keylogger on employee machine without consent.", "source": "manual", "source_details": {"note": "sample"}, "relevance_score": 0.95},
            {"content": "No workplace policy mentioned email monitoring.", "source": "manual", "source_details": {"note": "sample"}, "relevance_score": 0.9},
            {"content": "Personal emails accessed by IT revealing health information.", "source": "manual", "source_details": {"note": "sample"}, "relevance_score": 0.85},
        ]
        fs.add_facts_batch(sample_facts)

    pending = fs.get_pending_facts()

    # Non-interactive batch processing via approvals mapping
    if non_interactive:
        approvals = approvals or {}
        for idx, fact in enumerate(pending):
            action = approvals.get(idx, "approve")
            if isinstance(action, tuple) and action[0] == "edit":
                fs.update_fact(fact["id"], content=action[1])
                fs.approve_fact(fact["id"])
            elif action == "approve":
                fs.approve_fact(fact["id"])
            elif action == "reject":
                fs.reject_fact(fact["id"])
            else:
                # default: approve
                fs.approve_fact(fact["id"])

    else:
        # Interactive CLI loop
        for idx, fact in enumerate(pending):
            print("----------------------------------------")
            print(f"Fact #{idx}: {fact['content'][:200]}")
            print("(a)pprove / (r)eject / (e)dit / (s)kip / (q)uit")
            choice = input("Choice: ").strip().lower()
            if choice == "a":
                fs.approve_fact(fact["id"])
            elif choice == "r":
                fs.reject_fact(fact["id"])
            elif choice == "e":
                new_text = input("New text: ").strip()
                fs.update_fact(fact["id"], content=new_text)
                fs.approve_fact(fact["id"])
            elif choice == "q":
                break
            else:
                # skip or unknown -> leave pending
                continue

    # Lock approved facts to prevent re-retrieval downstream
    fs.lock_approved_facts()
    state["facts_approved_and_locked"] = True
    state["facts"] = fs.get_all_facts()

    return state


if __name__ == "__main__":
    print("Running interactive fact refiner (console). Use non-interactive for test automation.")
    s = interactive_refiner(non_interactive=False)
    print("Summary:", s.get("fact_storage").get_summary_stats())
