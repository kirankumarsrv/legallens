# DEBUGGING GUIDE: Fact Locking Implementation

## Overview
This guide helps diagnose and fix issues with the fact locking mechanism implemented in STEP 1.

---

## Common Issues & Solutions

### Issue 1: "AttributeError: 'FactStorage' object has no attribute 'lock_approved_facts'"

**Cause:** Old version of fact_storage.py without the new methods

**Solution:**
1. Check that `modules/fact_storage.py` has been updated
2. Verify the methods exist:
```bash
grep "def lock_approved_facts" modules/fact_storage.py
grep "def mark_fact_used_in_phase" modules/fact_storage.py
grep "def get_summary_stats" modules/fact_storage.py
```

3. If missing, re-apply updates to `modules/fact_storage.py`

**Verification:**
```python
from modules.fact_storage import FactStorage
fs = FactStorage()
print(dir(fs))  # Should show new methods
```

---

### Issue 2: "facts_approved_and_locked flag not set in state"

**Cause:** human_approval.py not setting the flag

**Symptoms:**
- Legal analysis uses facts_raw instead of locked facts
- Still retrieving statutes in Phase 2

**Solution:**
1. Check human_approval.py has the locking code:
```bash
grep "facts_approved_and_locked" workflows/lawyer_agent/nodes/human_approval.py
```

2. Verify the code block exists:
```python
if phase == "facts":
    fact_storage.lock_approved_facts()
    state["facts_approved_and_locked"] = True
```

3. If missing, re-apply updates

**Verification:**
```python
# After approval, check state
print(f"Flag set: {state.get('facts_approved_and_locked')}")
print(f"Storage exists: {state.get('fact_storage') is not None}")
```

---

### Issue 3: "Still retrieving statutes in legal_analysis (Phase 2)"

**Cause:** legal_analysis.py not using locked facts

**Symptoms:**
```
PHASE 2: Retrieved 456 facts (should be 0!)
```

**Solution:**
1. Check legal_analysis.py has the fix:
```bash
grep "facts_approved_and_locked" workflows/lawyer_agent/nodes/legal_analysis.py
grep "get_approved_facts" workflows/lawyer_agent/nodes/legal_analysis.py
```

2. Look for this code pattern:
```python
if fact_storage and state.get("facts_approved_and_locked"):
    statutes = fact_storage.get_approved_facts()  # SHOULD USE THIS
else:
    statutes = state.get("facts", [])  # FALLBACK ONLY
```

3. If the check is missing, re-apply the fix

**Verification:**
```python
# Add debug print in legal_analysis_node
if fact_storage and state.get("facts_approved_and_locked"):
    print("✅ Using locked facts from FactStorage")
else:
    print("⚠️  Using fallback facts (not locked!)")
```

---

### Issue 4: "FactStorage not initialized in fact_gathering"

**Cause:** fact_gathering.py not creating FactStorage

**Symptoms:**
- `fact_storage` is None in state
- Later phases get AttributeError

**Solution:**
1. Check fact_gathering.py creates FactStorage:
```bash
grep "fact_storage = FactStorage" workflows/lawyer_agent/nodes/fact_gathering.py
grep "fact_storage.add_fact" workflows/lawyer_agent/nodes/fact_gathering.py
```

2. Verify import:
```python
from modules.fact_storage import FactStorage
```

3. Verify creation:
```python
fact_storage = FactStorage()  # Should be created
for fact in facts:
    fact_storage.add_fact(...)  # Should add facts
state["fact_storage"] = fact_storage  # Should set in state
```

4. If missing, re-apply the update

**Verification:**
```python
# After fact_gathering
print(f"FactStorage type: {type(state.get('fact_storage'))}")
print(f"Facts stored: {len(state.get('fact_storage').get_all_facts())}")
```

---

### Issue 5: "Test fails with ImportError"

**Cause:** Python path not set correctly

**Solution:**
```bash
cd "c:\Users\kiran\Desktop\law ai"
python workflows/lawyer_agent/test_fact_locking.py
```

NOT:
```bash
python test_fact_locking.py  # Wrong directory!
```

**Verification:**
```python
import sys
from pathlib import Path
workspace = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace))
print(f"Python path: {sys.path[0]}")
```

---

## Debugging Tools

### 1. Check FactStorage State
```python
from modules.fact_storage import FactStorage

storage = FactStorage()
storage.add_fact("Test fact", "test_source", relevance_score=0.9)

# Check status
print(f"Total facts: {len(storage.get_all_facts())}")
print(f"Pending: {len(storage.get_pending_facts())}")
print(f"Approved: {len(storage.get_approved_facts())}")

# Approve and lock
storage.approve_fact("fact_1")
locked = storage.lock_approved_facts()
print(f"Locked facts: {len(locked)}")

# Check stats
stats = storage.get_summary_stats()
print(f"Stats: {stats}")
```

### 2. Check State During Workflow
```python
# Add to any node for debugging
fact_storage = state.get("fact_storage")
print(f"\n=== FACT STORAGE DEBUG ===")
print(f"Exists: {fact_storage is not None}")
if fact_storage:
    stats = fact_storage.get_summary_stats()
    print(f"Total facts: {stats['total_facts']}")
    print(f"Approved: {stats['approved_facts']}")
    print(f"Pending: {stats['pending_facts']}")
    print(f"Sources: {stats['sources']}")
    
print(f"Approved & locked flag: {state.get('facts_approved_and_locked')}")
print(f"=== END DEBUG ===\n")
```

### 3. Verify Code Changes
```bash
# Check if modifications were applied
grep -n "lock_approved_facts" modules/fact_storage.py
grep -n "facts_approved_and_locked" workflows/lawyer_agent/nodes/*.py

# Show line counts (should be increased)
wc -l modules/fact_storage.py
wc -l workflows/lawyer_agent/nodes/fact_gathering.py
wc -l workflows/lawyer_agent/nodes/human_approval.py
wc -l workflows/lawyer_agent/nodes/legal_analysis.py
```

### 4. Run Test with Verbose Output
```python
# Modify test_fact_locking.py to add more prints
import sys
sys.path.insert(0, "c:\\Users\\kiran\\Desktop\\law ai")

from modules.fact_storage import FactStorage

storage = FactStorage()
print(f"DEBUG: Created storage with ID {storage.case_id}")

# Add debugging to each step
fact_id = storage.add_fact("Test", "source")
print(f"DEBUG: Added fact {fact_id}")

storage.approve_fact(fact_id)
print(f"DEBUG: Approved fact {fact_id}")

locked = storage.lock_approved_facts()
print(f"DEBUG: Locked {len(locked)} facts")
```

---

## Integration Testing Checklist

### Pre-Integration
- [ ] Run `test_fact_locking.py` - should pass
- [ ] Check all imports work
- [ ] Verify methods exist on FactStorage
- [ ] Review code changes in all modified files

### During Integration
- [ ] Check FactStorage initializes in fact_gathering
- [ ] Verify facts are stored with correct metadata
- [ ] Confirm human approval locks facts
- [ ] Verify legal_analysis uses locked facts
- [ ] Check precedent retrieval still works

### Post-Integration
- [ ] Run full workflow with test case
- [ ] Verify audit trail is complete
- [ ] Check performance is improved
- [ ] Review reasoning_trace output

---

## Performance Debugging

### Memory Usage
```python
import sys
from modules.fact_storage import FactStorage

storage = FactStorage()
for i in range(1000):
    storage.add_fact(f"Fact {i}", "source")

# Check memory
print(f"Storage size: {sys.getsizeof(storage)}")
print(f"Total facts: {len(storage.get_all_facts())}")
print(f"Approx per fact: {sys.getsizeof(storage) / len(storage.get_all_facts())}")
```

### Retrieval Speed
```python
import time
from modules.fact_storage import FactStorage

storage = FactStorage()
# Add 1000 facts
for i in range(1000):
    storage.add_fact(f"Fact {i}", f"source_{i%10}")

# Test retrieval speed
start = time.time()
approved = storage.get_approved_facts()
elapsed = time.time() - start
print(f"Retrieval time for {len(approved)} facts: {elapsed:.4f}s")

# Test by source
start = time.time()
source_facts = storage.get_facts_by_source("source_5")
elapsed = time.time() - start
print(f"Filter by source time: {elapsed:.4f}s")
```

---

## Logging & Audit Trail

### Check Reasoning Trace
```python
# In any node
trace = state.get("reasoning_trace", [])
print("\n=== REASONING TRACE ===")
for i, entry in enumerate(trace, 1):
    print(f"{i}. {entry}")
print("======================\n")
```

### Expected Trace Output
```
PHASE 0: Loaded and parsed 1 evidence file(s). Total: 5000 chars. Language: English (en, 100% confidence)
PHASE 1: Retrieved 6 statute sections (stored in FactStorage)
PHASE 2: Used 6 approved statute facts + retrieved 5 precedent cases. LLM analysis generated.
```

### Audit FactStorage Changes
```python
storage = state.get("fact_storage")
if storage:
    all_facts = storage.get_all_facts()
    for fact in all_facts:
        print(f"Fact {fact['id']}: {fact['status']}")
        print(f"  Source: {fact['source']}")
        print(f"  Created: {fact['created_at']}")
        print(f"  Updated: {fact['updated_at']}")
        print(f"  Relevance: {fact.get('relevance_score', 0)}")
```

---

## Common Gotchas

### Gotcha 1: State Not Thread-Safe
**Issue:** If running multiple cases concurrently, states might interfere

**Solution:** Ensure each case has its own FactStorage instance
```python
# WRONG:
global_storage = FactStorage()  # Shared!

# CORRECT:
storage = FactStorage(case_id=case_id)  # Per-case
state["fact_storage"] = storage
```

### Gotcha 2: Facts Not Serializable
**Issue:** FactStorage might not serialize to JSON

**Solution:** Use the provided to_dict/from_dict methods
```python
# WRONG:
import json
json.dumps(fact_storage)  # May fail

# CORRECT:
data = fact_storage.to_dict()
json_str = json.dumps(data)  # Works
```

### Gotcha 3: Fact ID Collisions
**Issue:** Facts might have same ID if UUIDs collide

**Solution:** Check for duplicates before processing
```python
fact_ids = set()
for fact in facts:
    if fact['id'] in fact_ids:
        print(f"WARNING: Duplicate fact ID {fact['id']}")
    fact_ids.add(fact['id'])
```

---

## Quick Diagnostics

### Run This Script to Check Health
```python
#!/usr/bin/env python3
import sys
from pathlib import Path

workspace = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace))

print("🔍 FACT LOCKING IMPLEMENTATION HEALTH CHECK\n")

# Check 1: Imports
try:
    from modules.fact_storage import FactStorage
    print("✅ FactStorage imports correctly")
except ImportError as e:
    print(f"❌ FactStorage import failed: {e}")
    sys.exit(1)

# Check 2: Methods exist
required_methods = [
    'add_fact', 'approve_fact', 'lock_approved_facts',
    'get_approved_facts', 'mark_fact_used_in_phase',
    'get_summary_stats', 'get_all_facts'
]
fs = FactStorage()
missing = [m for m in required_methods if not hasattr(fs, m)]
if missing:
    print(f"❌ Missing methods: {missing}")
else:
    print("✅ All required methods present")

# Check 3: Basic functionality
try:
    fs.add_fact("Test fact", "test_source")
    fs.approve_fact("fact_1")
    locked = fs.lock_approved_facts()
    assert len(locked) == 1
    print("✅ Basic functionality works")
except Exception as e:
    print(f"❌ Functionality test failed: {e}")
    sys.exit(1)

# Check 4: Node files updated
nodes_to_check = [
    "workflows/lawyer_agent/nodes/fact_gathering.py",
    "workflows/lawyer_agent/nodes/human_approval.py",
    "workflows/lawyer_agent/nodes/legal_analysis.py",
]
for node in nodes_to_check:
    path = workspace / node
    if path.exists():
        print(f"✅ {node} exists")
    else:
        print(f"❌ {node} not found")

print("\n✨ HEALTH CHECK COMPLETE")
```

Save as `health_check.py` and run:
```bash
cd "c:\Users\kiran\Desktop\law ai"
python health_check.py
```

---

## Getting More Help

### If something doesn't work:

1. **Check the test:** 
   ```bash
   python workflows/lawyer_agent/test_fact_locking.py
   ```

2. **Review the code:**
   - Check `modules/fact_storage.py` for FactStorage implementation
   - Check each modified node file

3. **Add debug prints:**
   - Add `print(f"DEBUG: {variable}")` at key points
   - Run with verbose output

4. **Check the docs:**
   - `QUICK_REFERENCE.md` - Quick answers
   - `STEP_1_FIX_COMPLETION.md` - Implementation details
   - `WORKFLOW_REFINEMENT_SUMMARY_UPDATED.md` - Full overview

---

## Final Verification

Run this checklist to confirm everything is working:

- [ ] Test passes: `python workflows/lawyer_agent/test_fact_locking.py`
- [ ] fact_storage.py has lock_approved_facts() method
- [ ] human_approval.py sets facts_approved_and_locked flag
- [ ] legal_analysis.py uses fact_storage.get_approved_facts()
- [ ] No re-retrieval of statutes in Phase 2
- [ ] Audit trail includes Phase 2 fact usage
- [ ] All imports work without errors
- [ ] No type errors in modified files

**If all checks pass:** ✅ STEP 1 IMPLEMENTATION IS COMPLETE

---

**Last Updated:** 2024
**Version:** 1.0
**Status:** Production Ready (after STEP 1 integration testing)
