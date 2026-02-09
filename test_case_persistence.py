"""Test script to verify case persistence works correctly."""
import uuid
from modules.case_session_storage import CaseSessionStorage
from datetime import datetime, timezone

DB_PATH = "case_sessions.db"

def test_case_persistence():
    """Test creating, saving, and retrieving a case."""
    
    # Create a test case
    test_case_id = uuid.uuid4().hex
    test_case_name = "Test Case - Persistence Verification"
    test_case_type = "Theft"
    
    print(f"\n🧪 CASE PERSISTENCE TEST")
    print(f"{'='*50}")
    
    # Step 1: Create and save case
    print(f"\n1️⃣  Creating case: {test_case_id}")
    storage = CaseSessionStorage(test_case_id, DB_PATH)
    storage.set_case_status("in_progress")
    
    print(f"   Saving metadata...")
    now = datetime.now(timezone.utc).isoformat()
    storage.set_state_flag("case_name", test_case_name)
    storage.set_state_flag("case_type", test_case_type)
    storage.set_state_flag("created_at", now)
    storage.set_state_flag("updated_at", now)
    
    # Step 2: Verify case exists in database
    print(f"\n2️⃣  Verifying case was saved to database...")
    all_cases = CaseSessionStorage.get_all_cases(DB_PATH)
    if test_case_id in all_cases:
        print(f"   ✅ Case found in database!")
    else:
        print(f"   ❌ Case NOT found in database!")
        print(f"   Available cases: {all_cases}")
        return False
    
    # Step 3: Retrieve case data
    print(f"\n3️⃣  Retrieving case data...")
    retrieved_storage = CaseSessionStorage(test_case_id, DB_PATH)
    status = retrieved_storage.get_case_status()
    state_flags = retrieved_storage.get_all_state_flags()
    
    print(f"   Status: {status}")
    print(f"   Case Name: {state_flags.get('case_name')}")
    print(f"   Case Type: {state_flags.get('case_type')}")
    print(f"   Created At: {state_flags.get('created_at')}")
    
    # Step 4: Verify data integrity
    print(f"\n4️⃣  Verifying data integrity...")
    checks = [
        ("Case name matches", state_flags.get('case_name') == test_case_name),
        ("Case type matches", state_flags.get('case_type') == test_case_type),
        ("Status is correct", status == "in_progress"),
        ("Created timestamp set", state_flags.get('created_at') is not None),
    ]
    
    all_passed = True
    for check_name, result in checks:
        symbol = "✅" if result else "❌"
        print(f"   {symbol} {check_name}")
        if not result:
            all_passed = False
    
    # Step 5: Cleanup
    print(f"\n5️⃣  Cleaning up test case...")
    CaseSessionStorage.delete_case(test_case_id, DB_PATH)
    all_cases_after = CaseSessionStorage.get_all_cases(DB_PATH)
    if test_case_id not in all_cases_after:
        print(f"   ✅ Test case deleted successfully")
    else:
        print(f"   ❌ Test case was not deleted")
        all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print(f"✅ ALL TESTS PASSED - Case persistence is working!")
    else:
        print(f"❌ SOME TESTS FAILED - Check the output above")
    print(f"{'='*50}\n")
    
    return all_passed

if __name__ == "__main__":
    success = test_case_persistence()
    exit(0 if success else 1)
