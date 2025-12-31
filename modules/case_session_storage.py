"""
SQLite-backed persistent session storage for case workflow state.

Replaces `.case_session.json` with a proper database backend.
Stores: FactStorage, ArgumentStorage, prediction_history, metadata.

API:
    storage = CaseSessionStorage(case_id="case_123", db_path="./case_sessions.db")
    storage.save_facts(fact_storage)
    storage.save_arguments(argument_storage)
    storage.save_prediction_history(history_list)
    storage.set_state_flag(key, value)
    storage.get_state_flag(key)
    
    facts = storage.load_facts()
    arguments = storage.load_arguments()
    history = storage.load_prediction_history()
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class CaseSessionStorage:
    """SQLite-backed storage for case session state (facts, arguments, predictions)."""

    def __init__(self, case_id: str, db_path: str = "case_sessions.db"):
        """
        Initialize storage for a case.
        
        Args:
            case_id: Unique identifier for the case (used as primary key).
            db_path: Path to the SQLite database file.
        """
        self.case_id = case_id
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main session table (metadata)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_sessions (
                case_id TEXT PRIMARY KEY,
                created_at TEXT,
                updated_at TEXT,
                status TEXT DEFAULT 'in_progress'
            )
        """)

        # Facts table (FactStorage serialized JSON)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_facts (
                case_id TEXT PRIMARY KEY,
                facts_json TEXT,
                updated_at TEXT,
                FOREIGN KEY (case_id) REFERENCES case_sessions(case_id)
            )
        """)

        # Arguments table (ArgumentStorage serialized JSON)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_arguments (
                case_id TEXT PRIMARY KEY,
                arguments_json TEXT,
                updated_at TEXT,
                FOREIGN KEY (case_id) REFERENCES case_sessions(case_id)
            )
        """)

        # Prediction history table (list of predictions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                prediction_index INTEGER,
                prediction_json TEXT,
                created_at TEXT,
                FOREIGN KEY (case_id) REFERENCES case_sessions(case_id)
            )
        """)

        # State flags table (arbitrary key-value flags for workflow control)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_state_flags (
                case_id TEXT,
                flag_key TEXT,
                flag_value TEXT,
                updated_at TEXT,
                PRIMARY KEY (case_id, flag_key),
                FOREIGN KEY (case_id) REFERENCES case_sessions(case_id)
            )
        """)

        # Evidence metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                file_path TEXT,
                file_name TEXT,
                mime_type TEXT,
                size_bytes INTEGER,
                uploader TEXT,
                uploaded_at TEXT,
                FOREIGN KEY (case_id) REFERENCES case_sessions(case_id)
            )
        """)

        conn.commit()
        conn.close()

    def _ensure_case_session(self):
        """Ensure the case session row exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO case_sessions (case_id, created_at, updated_at) VALUES (?, ?, ?)",
            (self.case_id, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def save_facts(self, fact_storage_dict: Dict[str, Any]):
        """Save FactStorage to database."""
        self._ensure_case_session()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        facts_json = json.dumps(fact_storage_dict, default=str)
        cursor.execute(
            "INSERT OR REPLACE INTO case_facts (case_id, facts_json, updated_at) VALUES (?, ?, ?)",
            (self.case_id, facts_json, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def load_facts(self) -> Optional[Dict[str, Any]]:
        """Load FactStorage from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT facts_json FROM case_facts WHERE case_id = ?", (self.case_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return None
        return None

    def save_arguments(self, argument_storage_dict: Dict[str, Any]):
        """Save ArgumentStorage to database."""
        self._ensure_case_session()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        arguments_json = json.dumps(argument_storage_dict, default=str)
        cursor.execute(
            "INSERT OR REPLACE INTO case_arguments (case_id, arguments_json, updated_at) VALUES (?, ?, ?)",
            (self.case_id, arguments_json, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def load_arguments(self) -> Optional[Dict[str, Any]]:
        """Load ArgumentStorage from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT arguments_json FROM case_arguments WHERE case_id = ?", (self.case_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return None
        return None

    def save_prediction_history(self, history_list: List[Dict[str, Any]]):
        """Save full prediction history to database."""
        self._ensure_case_session()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear old history
        cursor.execute("DELETE FROM case_prediction_history WHERE case_id = ?", (self.case_id,))
        
        # Insert new history entries
        for idx, item in enumerate(history_list):
            prediction_json = json.dumps(item, default=str)
            cursor.execute(
                "INSERT INTO case_prediction_history (case_id, prediction_index, prediction_json, created_at) VALUES (?, ?, ?, ?)",
                (self.case_id, idx, prediction_json, datetime.utcnow().isoformat())
            )
        conn.commit()
        conn.close()

    def load_prediction_history(self) -> List[Dict[str, Any]]:
        """Load prediction history from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT prediction_index, prediction_json FROM case_prediction_history WHERE case_id = ? ORDER BY prediction_index ASC",
            (self.case_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            try:
                history.append(json.loads(row[1]))
            except Exception:
                pass
        return history

    def set_state_flag(self, flag_key: str, flag_value: Any):
        """Set a workflow control flag (e.g., 'facts_edited', 'restore_prediction_index')."""
        self._ensure_case_session()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        flag_value_str = json.dumps(flag_value) if not isinstance(flag_value, str) else flag_value
        cursor.execute(
            "INSERT OR REPLACE INTO case_state_flags (case_id, flag_key, flag_value, updated_at) VALUES (?, ?, ?, ?)",
            (self.case_id, flag_key, flag_value_str, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def get_state_flag(self, flag_key: str, default: Any = None) -> Any:
        """Get a workflow control flag."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT flag_value FROM case_state_flags WHERE case_id = ? AND flag_key = ?", (self.case_id, flag_key))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                return row[0]
        return default

    def clear_state_flag(self, flag_key: str):
        """Clear a state flag."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM case_state_flags WHERE case_id = ? AND flag_key = ?", (self.case_id, flag_key))
        conn.commit()
        conn.close()

    def get_all_state_flags(self) -> Dict[str, Any]:
        """Get all state flags for this case."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT flag_key, flag_value FROM case_state_flags WHERE case_id = ?", (self.case_id,))
        rows = cursor.fetchall()
        conn.close()
        
        flags = {}
        for key, value_str in rows:
            try:
                flags[key] = json.loads(value_str)
            except (json.JSONDecodeError, TypeError):
                flags[key] = value_str
        return flags

    def set_case_status(self, status: str):
        """Update case status (e.g., 'in_progress', 'completed', 'archived')."""
        self._ensure_case_session()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE case_sessions SET status = ?, updated_at = ? WHERE case_id = ?",
            (status, datetime.utcnow().isoformat(), self.case_id)
        )
        conn.commit()
        conn.close()

    def get_case_status(self) -> Optional[str]:
        """Get case status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM case_sessions WHERE case_id = ?", (self.case_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def clear_case_data(self):
        """Clear all data for this case (facts, arguments, history, flags)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM case_facts WHERE case_id = ?", (self.case_id,))
        cursor.execute("DELETE FROM case_arguments WHERE case_id = ?", (self.case_id,))
        cursor.execute("DELETE FROM case_prediction_history WHERE case_id = ?", (self.case_id,))
        cursor.execute("DELETE FROM case_state_flags WHERE case_id = ?", (self.case_id,))
        cursor.execute("DELETE FROM case_evidence WHERE case_id = ?", (self.case_id,))
        conn.commit()
        conn.close()

    def add_evidence_record(self, file_path: str, file_name: str, mime_type: str, size_bytes: int, uploader: str = 'anonymous'):
        """Add a single evidence file metadata record."""
        self._ensure_case_session()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO case_evidence (case_id, file_path, file_name, mime_type, size_bytes, uploader, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.case_id, file_path, file_name, mime_type, size_bytes, uploader, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def get_evidence_records(self) -> List[Dict[str, Any]]:
        """Return all evidence records for this case as list of dicts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_path, file_name, mime_type, size_bytes, uploader, uploaded_at FROM case_evidence WHERE case_id = ? ORDER BY uploaded_at ASC", (self.case_id,))
        rows = cursor.fetchall()
        conn.close()
        records = []
        for r in rows:
            records.append({
                "id": r[0],
                "file_path": r[1],
                "file_name": r[2],
                "mime_type": r[3],
                "size_bytes": r[4],
                "uploader": r[5],
                "uploaded_at": r[6],
            })
        return records

    @staticmethod
    def get_all_cases(db_path: str = "case_sessions.db") -> List[str]:
        """List all case IDs in the database."""
        if not os.path.exists(db_path):
            return []
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT case_id FROM case_sessions")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    @staticmethod
    def delete_case(case_id: str, db_path: str = "case_sessions.db"):
        """Delete all data for a case."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM case_facts WHERE case_id = ?", (case_id,))
        cursor.execute("DELETE FROM case_arguments WHERE case_id = ?", (case_id,))
        cursor.execute("DELETE FROM case_prediction_history WHERE case_id = ?", (case_id,))
        cursor.execute("DELETE FROM case_state_flags WHERE case_id = ?", (case_id,))
        cursor.execute("DELETE FROM case_sessions WHERE case_id = ?", (case_id,))
        conn.commit()
        conn.close()
