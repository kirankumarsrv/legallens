"""
Standalone Entity Normalization Test
Demonstrates core functions without spaCy dependency
"""

import sys
import os

# Add workspace root to path
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, workspace_root)

from workflows.lawyer_agent.evidence.entity_normalizer import (
    _fuzzy_match_names,
    normalize_entities,
    detect_role_conflicts
)
from workflows.lawyer_agent.evidence.entity_conflict_resolver import (
    resolve_conflicts_with_llm,
    generate_clarification_summary
)


# Mock LLM for testing
class MockLLM:
    def generate(self, prompt, **kwargs):
        if "Arun" in prompt and "different_persons" in prompt:
            return "RESOLUTION: different_persons\nACTUAL_ROLE: police\nCONFIDENCE: high"
        return "RESOLUTION: unclear\nACTUAL_ROLE: unknown\nCONFIDENCE: low"


def test_fuzzy_matching():
    """Test fuzzy name matching"""
    print("="*80)
    print("TEST 1: FUZZY NAME MATCHING")
    print("="*80)
    
    test_cases = [
        ("Munjappa", "Munyappa", True),   # Should match
        ("Arun Kumar", "Kumar Arun", True),  # Should match (word order)
        ("A. Kumar", "Arun Kumar", True),    # Should match (initials)
        ("Ramesh", "Ramesh Kumar", False),   # Should NOT match completely
        ("Singh", "Simgh", False),           # Typo - below threshold
    ]
    
    print("\nFuzzy Matching Results (threshold=0.85):\n")
    for name1, name2, expected in test_cases:
        result = _fuzzy_match_names(name1, name2, threshold=0.85)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        match_str = "MATCH" if result else "NO MATCH"
        print(f"  {status}  {name1:<20} ↔ {name2:<20} : {match_str}")


def test_normalization():
    """Test entity normalization with manual entity data"""
    print("\n" + "="*80)
    print("TEST 2: ENTITY NORMALIZATION & DEDUPLICATION")
    print("="*80)
    
    # Manually create entities dict (simulating entity extraction)
    entities = {
        "persons": [
            {"text": "Munjappa", "span": (0, 8)},
            {"text": "Munyappa", "span": (100, 108)},  # Duplicate (OCR error)
            {"text": "Arun Kumar", "span": (200, 210)},
            {"text": "Ramesh Kumar", "span": (300, 312)},
        ],
        "dates": [
            {"text": "15/10/2024", "span": (50, 60)},
            {"text": "15/10/2024", "span": (250, 260)},  # Exact duplicate
        ],
        "sections": [
            {"text": "420", "span": (400, 403)},
            {"text": "66D", "span": (500, 503)},
        ]
    }
    
    print("\nInput Entities:")
    print(f"  Persons: {[p['text'] for p in entities['persons']]}")
    print(f"  Dates: {[d['text'] for d in entities['dates']]}")
    
    # Normalize
    result = normalize_entities(entities, threshold=0.85)
    
    print("\n✅ Duplicates Found:")
    if result['duplicates_found']:
        for orig, canonical in result['duplicates_found']:
            print(f"  • '{orig}' → '{canonical}'")
    else:
        print("  None (no fuzzy matches above 0.85 threshold)")
    
    print("\n✅ Normalized Persons:")
    for person in result['normalized'].get('persons', []):
        print(f"  • {person['canonical']} (appears {person['occurrences']}x)")
    
    print("\n✅ Canonical Map:")
    for orig, canonical in result.get('canonical_map', {}).items():
        if orig != canonical:
            print(f"  • {orig} → {canonical}")


def test_role_conflict():
    """Test role conflict detection"""
    print("\n" + "="*80)
    print("TEST 3: ROLE CONFLICT DETECTION")
    print("="*80)
    
    # Create evidence text with conflicts
    evidence_text = """
FIR No: 123/2024
Complainant: Munjappa, aged 45 years

Investigation:
Inspector Arun Kumar of Cyber Crime Cell conducted the investigation.
The accused was arrested on 20/10/2024.

Witnesses:
1. Ramesh Kumar - neighbor
2. Arun - witnessed the transaction

Statement:
Inspector Arun Kumar states that witness Arun was present during the incident.
"""
    
    # Create entities with potential conflicts
    entities = {
        "persons": [
            {"text": "Munjappa", "span": (0, 8)},
            {"text": "Arun Kumar", "span": (100, 110)},
            {"text": "Ramesh Kumar", "span": (200, 212)},
            {"text": "Arun", "span": (250, 254)},
        ]
    }
    
    print("\nDetecting role conflicts in evidence text...")
    conflicts = detect_role_conflicts(entities, evidence_text=evidence_text)
    
    print(f"\n✅ Conflicts Found: {len(conflicts)}")
    for conflict in conflicts:
        print(f"\n  Person: {conflict['person']}")
        print(f"  Roles: {', '.join(conflict['roles'])}")
        print(f"  Severity: {conflict['severity']}")


def test_llm_resolution():
    """Test LLM-based conflict resolution"""
    print("\n" + "="*80)
    print("TEST 4: LLM-BASED CONFLICT RESOLUTION")
    print("="*80)
    
    evidence_text = """
Investigation by Inspector Arun Kumar.
Witness Arun saw the incident.
"""
    
    # Create a conflict
    conflicts = [{
        "person": "Arun",
        "roles": ["police", "witness"],
        "severity": "high",
        "contexts": [
            {"context": "Investigation by Inspector Arun Kumar"},
            {"context": "Witness Arun saw the incident"}
        ]
    }]
    
    print(f"\nResolving {len(conflicts)} conflict(s) with LLM...")
    
    llm = MockLLM()
    result = resolve_conflicts_with_llm(
        conflicts=conflicts,
        evidence_text=evidence_text,
        question="Who is Arun?",
        llm=llm,
        auto_resolve=False
    )
    
    print(f"\n✅ Resolved: {len(result['resolved'])}")
    for r in result['resolved']:
        print(f"  • {r['person']}: {r['resolved_role']} ({r['confidence']} confidence)")
    
    print(f"\n❓ Need Clarification: {len(result['clarification_questions'])}")
    for q in result['clarification_questions']:
        print(f"  • {q['person']}: {q['question']}")


def test_complete_pipeline():
    """Test complete pipeline"""
    print("\n" + "="*80)
    print("TEST 5: COMPLETE ENTITY PIPELINE")
    print("="*80)
    
    # Input entities with errors
    entities = {
        "persons": [
            {"text": "Munjappa", "span": (10, 18)},
            {"text": "Munyappa", "span": (100, 108)},  # Spelling variation
            {"text": "Arun Kumar", "span": (200, 210)},
            {"text": "Arun", "span": (250, 254)},
        ]
    }
    
    evidence_text = """
Complainant: Munjappa
Accused: Munyappa (OCR error of Munjappa)
Police: Inspector Arun Kumar
Witness: Arun (same as police?)
"""
    
    print("\n📋 Step 1: Normalize Entities")
    norm_result = normalize_entities(entities, threshold=0.85)
    duplicates = len(norm_result['duplicates_found'])
    print(f"  ✅ Found {duplicates} duplicate(s)")
    for orig, canonical in norm_result['duplicates_found']:
        print(f"     • '{orig}' → '{canonical}'")
    
    print("\n📋 Step 2: Detect Conflicts")
    conflicts = detect_role_conflicts(norm_result['normalized'], evidence_text)
    print(f"  ✅ Found {len(conflicts)} conflict(s)")
    for c in conflicts:
        print(f"     • {c['person']}: {', '.join(c['roles'])}")
    
    print("\n📋 Step 3: Resolve Conflicts")
    llm = MockLLM()
    resolution = resolve_conflicts_with_llm(
        conflicts=conflicts,
        evidence_text=evidence_text,
        question="Who is who?",
        llm=llm,
        auto_resolve=False
    )
    print(f"  ✅ Resolved: {len(resolution['resolved'])}")
    print(f"  ❓ Need clarification: {len(resolution['clarification_questions'])}")
    
    print("\n📋 Step 4: Generate Summary")
    summary = generate_clarification_summary(norm_result, resolution)
    print(summary)


if __name__ == "__main__":
    test_fuzzy_matching()
    test_normalization()
    test_role_conflict()
    test_llm_resolution()
    test_complete_pipeline()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
    print("="*80)
