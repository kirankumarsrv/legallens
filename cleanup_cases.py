"""Clean up all previous cases from the database."""
import os
import sqlite3
from modules.case_session_storage import CaseSessionStorage

DB_PATH = "case_sessions.db"

def cleanup_all_cases():
    """Delete all cases from the database."""
    try:
        # Get all cases
        case_ids = CaseSessionStorage.get_all_cases(DB_PATH)
        
        if not case_ids:
            print("No cases to delete.")
            return
        
        print(f"Found {len(case_ids)} cases to delete:")
        for case_id in case_ids:
            print(f"  - {case_id}")
        
        # Delete each case
        for case_id in case_ids:
            CaseSessionStorage.delete_case(case_id, DB_PATH)
            print(f"✓ Deleted case: {case_id}")
        
        print(f"\n✅ Successfully deleted all {len(case_ids)} cases!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_all_cases()
