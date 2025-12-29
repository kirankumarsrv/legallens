# STEP 2: BUILD FACT & EVIDENCE PERSISTENCE LAYER

## Overview
STEP 1 fixed the immediate fact re-retrieval bug by locking approved facts in-memory.

STEP 2 will extend this by:
1. **Persisting FactStorage** across session restarts
2. **Caching evidence** to prevent re-parsing
3. **Session management** - save/restore complete state
4. **Building evidence index** - quick lookup of case facts

## Problem to Solve
Currently:
- FactStorage lives only in RAM (session memory)
- If user closes browser/session, all facts are lost
- Evidence has to be re-parsed if session restarts
- No way to resume a case mid-analysis

## Solution Design

### 2.1 Session Persistence Layer
**File:** `modules/session_manager.py` (NEW)

```python
class SessionManager:
    """Manages session persistence for cases"""
    
    def save_session(case_id: str, state: LawyerState) -> None:
        """Save complete session to disk (JSON)"""
        # Save to: sessions/{case_id}/state.json
        # Includes: evidence, facts, analysis, all phases
    
    def load_session(case_id: str) -> LawyerState:
        """Load session from disk"""
        # Load from: sessions/{case_id}/state.json
        # Restore: evidence, facts, analysis, all phases
    
    def list_sessions() -> List[str]:
        """List all saved case sessions"""
        # Return case IDs with saved sessions
    
    def delete_session(case_id: str) -> None:
        """Delete a saved session"""
```

### 2.2 Evidence Caching Layer
**File:** `modules/evidence_cache.py` (NEW)

```python
class EvidenceCache:
    """Cache parsed evidence to avoid re-parsing"""
    
    def cache_evidence(
        file_paths: List[str],
        parsed_text: str,
        language: str,
        metadata: Dict
    ) -> str:
        """Store parsed evidence in cache"""
        # Store hash(file_paths) → parsed_text
        # Fast retrieval on re-upload of same files
    
    def get_cached_evidence(file_paths: List[str]) -> Optional[str]:
        """Retrieve previously cached evidence"""
        # Check if these files were already parsed
        # Return cached result if available
    
    def invalidate_cache(file_paths: List[str]) -> None:
        """Remove from cache (if file updated)"""
```

### 2.3 FactStorage Serialization
**Extend:** `modules/fact_storage.py`

Already has:
- `to_dict()` - Convert to JSON-serializable dict
- `from_dict()` - Restore from dict

Need to add:
- Save/load to file
- Version tracking (for backward compat)
- Compression (if storage grows large)

### 2.4 Evidence Index
**File:** `modules/evidence_index.py` (NEW)

```python
class EvidenceIndex:
    """Quick lookup of extracted entities & facts from evidence"""
    
    def build_from_evidence(evidence_text: str) -> EvidenceIndex:
        """Extract entities, dates, persons, sections from evidence"""
        # Uses: entity_extraction node
        # Builds index for fast lookups
    
    def find_references_by_entity(entity_type: str, entity_name: str):
        """Find all mentions of a person/date/section"""
        # e.g., find all mentions of "Suresh Kumar"
```

## Implementation Plan

### Phase A: Session Management (Days 1-2)
1. Create `SessionManager` class with save/load/list operations
2. Add session persistence to state in `graph.py`
3. Test: Save a session, close it, reload it
4. Expected: State fully restored with all facts, evidence, analysis

### Phase B: Evidence Caching (Days 2-3)
1. Create `EvidenceCache` with hash-based lookup
2. Update `evidence_ingest_node` to check cache first
3. Test: Re-upload same file → use cached result
4. Expected: No re-parsing overhead for duplicate uploads

### Phase C: FactStorage File Persistence (Days 3-4)
1. Add `save_to_file()` and `load_from_file()` methods
2. Update `SessionManager` to handle FactStorage
3. Test: Save facts to file, load in new session
4. Expected: Facts fully restored with audit trail intact

### Phase D: Evidence Index (Days 4-5)
1. Create `EvidenceIndex` class
2. Build index during evidence ingestion
3. Connect to entity extraction outputs
4. Test: Query index for specific entities
5. Expected: Fast entity lookups without re-parsing

## File Structure
```
law ai/
├── modules/
│   ├── fact_storage.py (existing - extend)
│   ├── session_manager.py (NEW)
│   ├── evidence_cache.py (NEW)
│   └── evidence_index.py (NEW)
├── sessions/ (NEW - auto-created)
│   ├── case_001/
│   │   ├── state.json
│   │   ├── evidence_original.txt
│   │   ├── facts.json
│   │   └── metadata.json
│   └── case_002/
└── cache/ (NEW - auto-created)
    ├── evidence_abc123def456.txt
    └── evidence_hash.json
```

## Testing Strategy

### Unit Tests
- ✅ FactStorage serialization/deserialization
- ✅ SessionManager save/restore
- ✅ EvidenceCache hit/miss
- ✅ EvidenceIndex queries

### Integration Tests
- ✅ Full session persistence workflow
- ✅ Evidence caching in fact_gathering
- ✅ State recovery after "crash"
- ✅ Multiple concurrent sessions

### Performance Tests
- ✅ Session save time (< 1s)
- ✅ Session load time (< 1s)
- ✅ Evidence cache hit rate

## Benefits

### For Users
- Resume cases mid-analysis
- No re-uploading evidence
- Sessions auto-save
- Can switch between cases

### For System
- Reduced LLM calls
- Less vector DB queries
- Better performance
- Audit trail preserved

## Success Criteria
- [x] STEP 1: Facts locked after approval ← COMPLETED
- [ ] Session can be saved to disk
- [ ] Session can be restored from disk
- [ ] Evidence caching prevents re-parsing
- [ ] FactStorage fully serialized/deserialized
- [ ] Multiple sessions managed independently
- [ ] Audit trail preserved across sessions

## Migration Path

1. **STEP 1 (DONE):** Fix fact re-retrieval bug
2. **STEP 2 (NEXT):** Build persistence layer
3. **STEP 3:** Test complete workflow (with persistence)
4. **STEP 4:** Optimize vector DB usage
5. **STEP 5:** Build UI for session management
6. **STEP 6:** Deploy & document

## Related Issues
- Session-scoped evidence (PRIVACY)
- Evidence file tracking (AUDIT)
- Case organization (UX)
- Fact versioning (TRACEABILITY)
