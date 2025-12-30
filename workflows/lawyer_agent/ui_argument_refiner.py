"""Streamlit UI for interactive argument refinement.

Run:
    streamlit run workflows/lawyer_agent/ui_argument_refiner.py

Mirrors the fact refiner UI: edit/approve/reject arguments stored in ArgumentStorage
persisted to `.case_session.json`.
"""
import json
import os
import sys

# Ensure project root is importable when Streamlit executes this file
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

from modules.argument_storage import ArgumentStorage

SESSION_FILE = ".case_session.json"


def load_argument_storage(path: str = SESSION_FILE) -> ArgumentStorage:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # session may contain an 'argument_storage' key or full dump
            arg_data = data.get("argument_storage") if isinstance(data, dict) else None
            if arg_data:
                return ArgumentStorage.from_dict(arg_data)
            # fallback if entire file is ArgumentStorage dict
            if data and isinstance(data, dict) and any(k in data for k in ("arguments", "approved_arg_ids")):
                return ArgumentStorage.from_dict(data)
        except Exception as e:
            st.warning(f"Failed to load session file: {e}")
    return ArgumentStorage()


def save_argument_storage(as_store: ArgumentStorage, path: str = SESSION_FILE) -> None:
    try:
        # Merge into existing session file if present
        session = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    session = json.load(f) or {}
            except Exception:
                session = {}

        session["argument_storage"] = as_store.to_dict()
        # Signal that arguments were edited so prediction can be recomputed
        session["arguments_edited"] = True
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)
    except Exception as e:
        st.warning(f"Failed to save session file: {e}")


def do_rerun():
    rerun_fn = getattr(st, "experimental_rerun", None)
    if callable(rerun_fn):
        try:
            rerun_fn()
            return
        except Exception:
            pass
    st.info("Please refresh the page to see updates.")
    st.stop()


def seed_sample_arguments(as_store: ArgumentStorage):
    if as_store.get_all_arguments():
        return
    sample = [
        {"content": "Employer's monitoring without consent violates Article 21 privacy.", "legal_basis": "Article 21", "relevance_score": 0.95},
        {"content": "Keylogger installation may attract IPC sections re: unauthorized access.", "legal_basis": "IPC", "relevance_score": 0.9},
    ]
    as_store.add_arguments_batch(sample)


def main():
    st.set_page_config(page_title="Argument Refiner", layout="wide")
    st.title("Interactive Argument Refiner")

    as_store = load_argument_storage()

    st.sidebar.header("Session")
    if st.sidebar.button("Seed sample arguments"):
        seed_sample_arguments(as_store)
        save_argument_storage(as_store)
        do_rerun()

    st.sidebar.markdown(f"**Arguments:** {len(as_store.get_all_arguments())}")
    st.sidebar.markdown(f"**Approved:** {len(as_store.approved_arg_ids)}")
    st.sidebar.markdown(f"**Pending:** {len(as_store.get_pending_arguments())}")

    if st.sidebar.button("Lock approved arguments"):
        as_store.lock_approved_arguments()
        save_argument_storage(as_store)
        st.success("Approved arguments locked.")

    if st.sidebar.button("Clear arguments"):
        as_store = ArgumentStorage()
        save_argument_storage(as_store)
        do_rerun()

    args = as_store.get_all_arguments()
    if not args:
        st.info("No arguments found. Run legal analysis to generate arguments or seed sample.")
        return

    for arg in args:
        arg_id = arg["id"]
        with st.expander(f"Argument: {arg['content'][:80]}"):
            col1, col2 = st.columns([4, 1])
            with col1:
                new_text = st.text_area(f"edit_{arg_id}", value=arg["content"], key=f"txt_{arg_id}")
                if new_text != arg["content"]:
                    if st.button("Update text", key=f"update_{arg_id}"):
                        as_store.update_argument(arg_id, content=new_text)
                        save_argument_storage(as_store)
                        do_rerun()

            with col2:
                status = arg.get("status", "pending")
                status_map = {"pending": "pending", "approved": "approve", "approved_locked": "approve", "rejected": "reject"}
                default = status_map.get(status, "pending")
                opts = ["pending", "approve", "reject"]
                idx = opts.index(default) if default in opts else 0
                action = st.selectbox(f"action_{arg_id}", options=opts, index=idx, key=f"action_{arg_id}")
                if st.button("Apply", key=f"apply_{arg_id}"):
                    if action == "approve":
                        as_store.approve_argument(arg_id)
                        st.success("Approved")
                    elif action == "reject":
                        as_store.reject_argument(arg_id)
                        st.warning("Rejected")
                    else:
                        st.info("Left pending")
                    save_argument_storage(as_store)
                    do_rerun()

    # Prediction history & restore
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
                if st.sidebar.button(f"Restore #{display_idx} — {ts}", key=f"restore_arg_{display_idx}"):
                    session["restore_prediction_index"] = display_idx
                    with open(SESSION_FILE, "w", encoding="utf-8") as f:
                        json.dump(session, f, indent=2)
                    st.sidebar.success(f"Wrote restore index {display_idx} to session. Run workflow to apply.")
    except Exception:
        st.sidebar.warning("Failed to read prediction history from session file.")

    approved = as_store.get_approved_arguments()
    if approved:
        st.header("Approved Arguments")
        approved_text = "\n\n".join([a["content"] for a in approved])
        st.text_area("approved_text", value=approved_text, height=200)
        if st.button("Download approved arguments (.txt)"):
            st.download_button("Download", approved_text, file_name="approved_arguments.txt")


if __name__ == "__main__":
    main()
