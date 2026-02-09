# Entity Extraction & Normalization in Workflow 1

## Overview

Workflow 1 now includes **intelligent entity processing** to reduce hallucinations and handle real-world legal document issues:

1. **Named Entity Recognition (NER)** - Extract persons, dates, sections, FIRs, etc.
2. **Fuzzy Matching** - Handle name variations (Munjappa ↔ Munyappa)
3. **Deduplication** - Merge similar entities
4. **Conflict Detection** - Find role conflicts (Police: Arun, Accused: Arun)
5. **LLM Resolution** - Use AI to resolve ambiguous cases
6. **Lawyer Clarification** - Generate questions for unresolved conflicts

---

## New Workflow 1 Flow

```
Evidence Ingest
    ↓
Entity Extraction (NER)
    ↓
Entity Normalization (Fuzzy Matching + Deduplication)
    ↓  
Conflict Detection & Resolution (LLM)
    ↓
Fact Gathering
    ↓
END
```

---

## Features

### 1. **Name Variation Handling**

**Problem:** Legal documents often have OCR errors or spelling variations
- "Munjappa" vs "Munyappa"
- "Arun Kumar" vs "Kumar Arun"
- "A. Kumar" vs "Arun Kumar"

**Solution:** Fuzzy matching with 85% similarity threshold
- Uses `difflib.SequenceMatcher`
- Token-based matching (handles word order)
- Initials matching

**Example:**
```python
# Input entities
persons = ["Munjappa", "Munyappa", "Arun Kumar", "Kumar Arun"]

# After normalization
normalized_persons = [
    {"canonical": "Munjappa", "occurrences": 2},  # Merged "Munyappa"
    {"canonical": "Arun Kumar", "occurrences": 2}  # Merged "Kumar Arun"
]
```

### 2. **Role Conflict Detection**

**Problem:** Same person appearing in different roles
- Police: Arun Kumar
- Witness: Arun (same person?)
- Accused: Munjappa (but Munjappa is the victim!)

**Solution:** Pattern matching + context analysis
- Detects role keywords (police, accused, victim, witness)
- Finds person names near role keywords
- Flags conflicts for review

**Severity Levels:**
- **High:** Police ↔ Accused (critical conflict)
- **Medium:** Victim ↔ Witness (possible but needs verification)
- **Low:** Other combinations

### 3. **LLM-Based Conflict Resolution**

**Problem:** Some conflicts need context understanding
- Is "Arun" the same as "Inspector Arun Kumar"?
- Is "Munyappa" the accused or a victim name variation?

**Solution:** LLM analyzes evidence context
- Reads full evidence text
- Analyzes role contexts
- Determines most likely interpretation
- Provides confidence level (high/medium/low)

**LLM Output Format:**
```
RESOLUTION: same_person / different_persons / unclear
ACTUAL_ROLE: police / accused / victim / witness / other
CONFIDENCE: high / medium / low
REASONING: Brief explanation
CLARIFICATION_NEEDED: YES / NO
QUESTION_FOR_LAWYER: What to ask lawyer
```

### 4. **Lawyer Clarification Questions**

**Problem:** Not all conflicts can be auto-resolved

**Solution:** Generate specific questions for lawyer
- Shows context where conflict appears
- Provides suggested resolution
- Allows manual override

**Example Output:**
```markdown
## ⚠️ Conflicts Requiring Clarification (2)

### 1. Arun
**Question:** Please confirm: Is witness "Arun" the same as Inspector Arun Kumar?
**Context:** ...investigation conducted by Inspector Arun Kumar...
               ...witness Arun witnessed the transaction...

### 2. Munjappa
**Question:** Confirm: Is Munjappa the victim or accused?
**Context:** ...Complainant: Munjappa...
               ...accused Munyappa had created fake profiles...
```

---

## Configuration

### Enable/Disable Features

```python
from workflows.lawyer_agent.workflow_1_fact_retrieval import run_fact_retrieval_workflow

state = run_fact_retrieval_workflow(
    state=state,
    chroma_stores=chroma_stores,
    embedding_model=embedding_model,
    llm=llm,
    
    # Entity processing controls
    enable_entity_extraction=True,      # Enable NER
    enable_entity_normalization=True,   # Enable fuzzy matching
    auto_resolve_conflicts=False,       # Don't auto-resolve, ask lawyer
    similarity_threshold=0.85           # 85% similarity for fuzzy match
)
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_entity_extraction` | `True` | Enable NER (persons, dates, sections, etc.) |
| `enable_entity_normalization` | `True` | Enable fuzzy matching and deduplication |
| `auto_resolve_conflicts` | `False` | Auto-resolve high-confidence conflicts |
| `similarity_threshold` | `0.85` | Fuzzy matching threshold (0.0-1.0) |

---

## State Fields Added

New fields in `LawyerState`:

```python
# Normalized entities (deduplicated, fuzzy-matched)
normalized_entities: Optional[Dict[str, Any]]

# Entity conflicts detected (same person in multiple roles)
entity_conflicts: Optional[List[Dict[str, Any]]]

# Clarification questions for lawyer (ambiguous entities)
entity_clarifications: Optional[List[Dict[str, Any]]]

# Human-readable entity summary (markdown)
entity_summary: Optional[str]

# Canonical mapping for entity names (original -> canonical)
entity_canonical_map: Optional[Dict[str, str]]
```

---

## Testing

Run the test script:

```bash
python workflows/lawyer_agent/test_entity_normalization.py
```

**Output:**
```
FUZZY MATCHING TEST
Munjappa             ↔ Munyappa            : ✅ MATCH
Arun Kumar           ↔ Kumar Arun          : ✅ MATCH
A. Kumar             ↔ Arun Kumar          : ✅ MATCH

ENTITY EXTRACTION & NORMALIZATION TEST
1️⃣  EXTRACTING ENTITIES...
PERSONS: 5 found
  • Munjappa
  • Munyappa
  • Arun Kumar
  ...

2️⃣  NORMALIZING ENTITIES...
Duplicates found: 2
  ✅ 'Munyappa' → 'Munjappa'
  ✅ 'Kumar Arun' → 'Arun Kumar'

3️⃣  DETECTING ROLE CONFLICTS...
Conflicts found: 2
⚠️  Person: Arun
   Roles: police, witness
   Severity: high

4️⃣  RESOLVING CONFLICTS WITH LLM...
Need clarification: 2
  ❓ Arun
     Please confirm: Is witness "Arun" the same as Inspector Arun Kumar?
```

---

## Files Created

| File | Purpose |
|------|---------|
| `entity_normalizer.py` | Fuzzy matching, deduplication, conflict detection |
| `entity_conflict_resolver.py` | LLM-based resolution, clarification generation |
| `nodes/entity_normalization.py` | Node that orchestrates normalization |
| `test_entity_normalization.py` | Test script with examples |

---

## Usage in API

The entity clarifications are automatically generated during Workflow 1 and can be retrieved via:

```python
# After running Workflow 1
result = run_fact_retrieval_workflow(state, ...)

# Check for clarifications
if result.get("entity_clarifications"):
    for question in result["entity_clarifications"]:
        print(f"❓ {question['person']}: {question['question']}")
        
# Get human-readable summary
if result.get("entity_summary"):
    print(result["entity_summary"])
```

---

## Benefits

✅ **Reduces Hallucinations** - Standardizes entity names across document
✅ **Handles Real-world Issues** - OCR errors, typos, name variations
✅ **Detects Conflicts** - Flags logical inconsistencies for review
✅ **Context-Aware** - Uses LLM to understand ambiguous cases
✅ **Lawyer-in-the-Loop** - Generates specific questions for manual verification
✅ **Transparent** - Shows all disambiguations and conflicts

---

## Next Steps

1. **Test with real FIR documents**
2. **Tune similarity threshold** based on accuracy
3. **Add more role patterns** (judge, complainant, etc.)
4. **Integrate with UI** to show clarification questions
5. **Add manual override** API for lawyer corrections
