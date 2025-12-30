"""Streamlit UI for interactive fact refinement.

Run:
    streamlit run workflows/lawyer_agent/ui_streamlit.py

Features:
 - Load or create `FactStorage` persisted to `.case_session.json`
 - Display facts with editable text areas
 - Approve / Reject / Keep (pending) actions per fact
 - Lock approved facts to prevent re-retrieval
 - Export approved facts text
"""
import json
import os
import sys
from typing import Dict

# Ensure project root is importable when Streamlit executes this file
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

from modules.fact_storage import FactStorage


SESSION_FILE = ".case_session.json"


def load_storage(path: str = SESSION_FILE) -> FactStorage:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FactStorage.from_dict(data)
        except Exception as e:
            st.warning(f"Failed to load session file: {e}")
    return FactStorage()


def do_rerun():
    """Try to programmatically rerun the Streamlit app; fallback to a refresh instruction."""
    rerun_fn = getattr(st, "experimental_rerun", None)
    if callable(rerun_fn):
        try:
            rerun_fn()
            return
        except Exception:
            pass

    # Fallback: instruct user to refresh and stop script execution
    st.info("Please refresh the page to see updates.")
    st.stop()


def save_storage(fs: FactStorage, path: str = SESSION_FILE) -> None:
    try:
        # Merge into existing session file if present
        session = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    session = json.load(f) or {}
            except Exception:
                session = {}

        # Update fact storage content
        session.update(fs.to_dict())

        # If this save indicates a user edit, set a flag for recompute
        session["facts_edited"] = True

        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)
    except Exception as e:
        st.warning(f"Failed to save session file: {e}")


def seed_sample_facts(fs: FactStorage):
    if fs.get_all_facts():
        return
    sample_facts = [
        {"content": "Employer installed keylogger on employee machine without consent.", "source": "manual", "source_details": {"note": "sample"}, "relevance_score": 0.95},
        {"content": "No workplace policy mentioned email monitoring.", "source": "manual", "source_details": {"note": "sample"}, "relevance_score": 0.9},
        {"content": "Personal emails accessed by IT revealing health information.", "source": "manual", "source_details": {"note": "sample"}, "relevance_score": 0.85},
    ]
    fs.add_facts_batch(sample_facts)


def main():
    st.set_page_config(page_title="Fact Refiner", layout="wide")
    st.title("Interactive Fact Refiner")

    fs = load_storage()

    st.sidebar.header("Session")
    if st.sidebar.button("Seed sample facts"):
        seed_sample_facts(fs)
        save_storage(fs)
        do_rerun()

    st.sidebar.markdown(f"**Facts:** {len(fs.get_all_facts())}")
    st.sidebar.markdown(f"**Approved:** {len(fs.approved_fact_ids)}")
    st.sidebar.markdown(f"**Pending:** {len(fs.get_pending_facts())}")

    st.sidebar.write("")
    if st.sidebar.button("Lock approved facts"):
        fs.lock_approved_facts()
        save_storage(fs)
        st.success("Approved facts locked.")

    st.sidebar.write("")
    if st.sidebar.button("Clear session"):
        fs.clear()
        save_storage(fs)
        do_rerun()

    # Main area: list facts
    facts = fs.get_all_facts()
    if not facts:
        st.info("No facts in session. Use 'Seed sample facts' or run retrieval node to populate.")
        return

    for fact in facts:
        fact_id = fact["id"]
        with st.expander(f"Fact: {fact['content'][:80]}"):
            col1, col2 = st.columns([4, 1])
            with col1:
                new_text = st.text_area(f"edit_{fact_id}", value=fact["content"], key=f"txt_{fact_id}")
                if new_text != fact["content"]:
                    if st.button("Update text", key=f"update_{fact_id}"):
                        fs.update_fact(fact_id, content=new_text)
                        save_storage(fs)
                        do_rerun()

            with col2:
                status = fact.get("status", "pending")
                # Map fact status to UI action (handle all possible statuses)
                status_to_action = {
                    "pending": "pending",
                    "approve": "approve",
                    "approved": "approve",
                    "approved_locked": "approve",
                    "reject": "reject",
                    "rejected": "reject",
                }
                action_default = status_to_action.get(status, "pending")
                action_options = ["pending", "approve", "reject"]
                action_index = action_options.index(action_default) if action_default in action_options else 0
                
                action = st.selectbox(f"action_{fact_id}", options=action_options, index=action_index, key=f"action_{fact_id}")
                if st.button("Apply", key=f"apply_{fact_id}"):
                    if action == "approve":
                        fs.approve_fact(fact_id)
                        st.success("Approved")
                    elif action == "reject":
                        fs.reject_fact(fact_id)
                        st.warning("Rejected")
                    else:
                        st.info("Left pending")
                    save_storage(fs)
                    do_rerun()

    # Prediction history & restore (reads session file)
    st.sidebar.write("")
    st.sidebar.header("Prediction History")
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                session = json.load(f) or {}
        else:
            session = {}
        history = session.get("prediction_history") or []
        if not history:
            st.sidebar.info("No prediction history available.")
        else:
            for idx, item in enumerate(reversed(history)):
                display_idx = len(history) - 1 - idx
                ts = item.get("timestamp", "?")
                preview = (item.get("prediction") or "")[:120]
                if st.sidebar.button(f"Restore #{display_idx} — {ts}", key=f"restore_{display_idx}"):
                    # write restore flag to session file for the workflow runner to pick up
                    session["restore_prediction_index"] = display_idx
                    with open(SESSION_FILE, "w", encoding="utf-8") as f:
                        json.dump(session, f, indent=2)
                    st.sidebar.success(f"Wrote restore index {display_idx} to session. Run workflow to apply.")
    except Exception:
        st.sidebar.warning("Failed to read prediction history from session file.")

    # Export approved facts text
    approved = fs.get_approved_facts()
    if approved:
        st.header("Approved Facts")
        approved_text = fs.get_approved_facts_content()
        st.text_area("approved_text", value=approved_text, height=200)
        if st.button("Download approved facts (.txt)"):
            st.download_button("Download", approved_text, file_name="approved_facts.txt")


if __name__ == "__main__":
    main()
