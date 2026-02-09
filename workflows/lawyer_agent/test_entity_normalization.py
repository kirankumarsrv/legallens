"""
Test Entity Extraction and Normalization Pipeline

Demonstrates:
1. Entity extraction (NER)
2. Fuzzy name matching (Munjappa vs Munyappa)
3. Role conflict detection (Police: Arun, Accused: Arun)
4. LLM-based conflict resolution
"""

import sys
import os

# Add workspace root to path
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, workspace_root)

from workflows.lawyer_agent.evidence.entity_extractor import extract_entities
from workflows.lawyer_agent.evidence.entity_normalizer import (
    normalize_entities,
    detect_role_conflicts
)
from workflows.lawyer_agent.evidence.entity_conflict_resolver import (
    resolve_conflicts_with_llm,
    generate_clarification_summary
)


# Sample evidence with name variations and role conflicts
SAMPLE_EVIDENCE = """
FIR No: 123/2024
Police Station: Bangalore Cyber Crime Cell

Complainant: Munjappa, aged 45 years, residing at Jayanagar, Bangalore

Statement of Complaint:
I, Munjappa, hereby state that on 15/10/2024, I was defrauded by the accused.
The investigation was conducted by Inspector Arun Kumar of Cyber Crime Cell.

Investigation Report:
During investigation, it was found that the accused Munyappa had created fake 
profiles using stolen documents. The accused was arrested on 20/10/2024.

Witnesses:
1. Ramesh Kumar - neighbor of complainant
2. Arun - witnessed the transaction (same person as investigating officer)

Accused Details:
Name: Munyappa (also known as Munjappa)
Age: 45 years
Address: Jayanagar, Bangalore

Sections: Section 420 IPC, Section 66D IT Act

Signed by: Inspector Arun Kumar
Date: 25/10/2024
"""


# Mock LLM for testing
class MockLLM:
    def generate(self, prompt, **kwargs):
        # Simulate LLM response for conflict resolution
        if "Arun" in prompt:
            return """RESOLUTION: different_persons
ACTUAL_ROLE: police
CONFIDENCE: high
REASONING: Inspector Arun Kumar is the investigating officer. The witness "Arun" mentioned separately is likely a different person with the same first name. Police officers cannot be witnesses in their own investigations.
CLARIFICATION_NEEDED: YES
QUESTION_FOR_LAWYER: Please confirm: Is witness "Arun" the same as Inspector Arun Kumar, or a different person?"""
        
        elif "Munjappa" in prompt or "Munyappa" in prompt:
            return """RESOLUTION: same_person
ACTUAL_ROLE: victim
CONFIDENCE: high
REASONING: "Munjappa" and "Munyappa" are spelling variations of the same name (common in Indian names). The person is clearly the complainant/victim based on context. The "accused Munyappa" mention appears to be an OCR or transcription error.
CLARIFICATION_NEEDED: YES
QUESTION_FOR_LAWYER: Confirm: Is Munjappa the victim or accused? The document shows conflicting information."""
        
        return "Unable to resolve conflict"


def test_entity_pipeline():
    """Test complete entity extraction and normalization pipeline"""
    
    print("="*80)
    print("ENTITY EXTRACTION & NORMALIZATION TEST")
    print("="*80)
    
    # Step 1: Extract entities
    print("\n1️⃣  EXTRACTING ENTITIES...")
    print("-" * 80)
    entities = extract_entities(SAMPLE_EVIDENCE)
    
    for category, entity_list in entities.items():
        print(f"\n{category.upper()}: {len(entity_list)} found")
        for entity in entity_list[:5]:  # Show first 5
            print(f"  • {entity['text']}")
    
    # Step 2: Normalize entities
    print("\n\n2️⃣  NORMALIZING ENTITIES (Fuzzy Matching)...")
    print("-" * 80)
    normalization_result = normalize_entities(entities, threshold=0.85)
    
    print(f"\nDuplicates found: {len(normalization_result['duplicates_found'])}")
    for orig, canonical in normalization_result['duplicates_found']:
        print(f"  ✅ '{orig}' → '{canonical}'")
    
    print(f"\nNormalized entities:")
    for category, entity_list in normalization_result['normalized'].items():
        print(f"\n{category.upper()}: {len(entity_list)} unique")
        for entity in entity_list[:5]:
            print(f"  • {entity['canonical']} (appears {entity['occurrences']}x)")
    
    # Step 3: Detect role conflicts
    print("\n\n3️⃣  DETECTING ROLE CONFLICTS...")
    print("-" * 80)
    conflicts = detect_role_conflicts(
        normalization_result['normalized'],
        evidence_text=SAMPLE_EVIDENCE
    )
    
    print(f"\nConflicts found: {len(conflicts)}")
    for conflict in conflicts:
        print(f"\n⚠️  Person: {conflict['person']}")
        print(f"   Roles: {', '.join(conflict['roles'])}")
        print(f"   Severity: {conflict['severity']}")
        print(f"   Contexts:")
        for ctx in conflict.get('contexts', [])[:2]:
            print(f"     - {ctx['context'][:100]}...")
    
    # Step 4: LLM-based conflict resolution
    print("\n\n4️⃣  RESOLVING CONFLICTS WITH LLM...")
    print("-" * 80)
    llm = MockLLM()
    
    conflict_resolution = resolve_conflicts_with_llm(
        conflicts=conflicts,
        evidence_text=SAMPLE_EVIDENCE,
        question="FIR analysis for cyber fraud case",
        llm=llm,
        auto_resolve=False  # Generate questions for lawyer
    )
    
    print(f"\nResolved: {len(conflict_resolution['resolved'])}")
    for resolved in conflict_resolution['resolved']:
        print(f"  ✅ {resolved['person']}: {resolved['resolved_role']} ({resolved['confidence']} confidence)")
        print(f"     {resolved['reasoning'][:100]}...")
    
    print(f"\nNeed clarification: {len(conflict_resolution['clarification_questions'])}")
    for question in conflict_resolution['clarification_questions']:
        print(f"\n  ❓ {question['person']}")
        print(f"     {question['question']}")
    
    # Step 5: Generate summary
    print("\n\n5️⃣  GENERATING SUMMARY FOR LAWYER REVIEW...")
    print("-" * 80)
    summary = generate_clarification_summary(normalization_result, conflict_resolution)
    print(summary)
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


def test_fuzzy_matching_only():
    """Test just the fuzzy matching logic"""
    
    print("\n" + "="*80)
    print("FUZZY MATCHING TEST")
    print("="*80)
    
    test_cases = [
        ("Munjappa", "Munyappa"),  # Similar Indian name
        ("Arun Kumar", "Kumar Arun"),  # Name order
        ("A. Kumar", "Arun Kumar"),  # Initials
        ("Ramesh", "Ramesh Kumar"),  # Partial match
        ("Singh", "Simgh"),  # Typo
    ]
    
    from workflows.lawyer_agent.evidence.entity_normalizer import _fuzzy_match_names
    
    for name1, name2 in test_cases:
        match = _fuzzy_match_names(name1, name2, threshold=0.85)
        print(f"\n{name1:<20} ↔ {name2:<20} : {'✅ MATCH' if match else '❌ NO MATCH'}")


if __name__ == "__main__":
    test_fuzzy_matching_only()
    print("\n\n")
    test_entity_pipeline()
