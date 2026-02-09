"""
Entity Normalization and Deduplication

Handles:
1. Fuzzy matching for name variations (Munjappa vs Munyappa)
2. Deduplication of similar entities
3. Detection of role conflicts (same person in different roles)
"""

from typing import Dict, List, Any, Tuple
from difflib import SequenceMatcher
from collections import defaultdict


def _calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)"""
    return SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()


def _fuzzy_match_names(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """
    Check if two names are likely the same person.
    
    Uses multiple techniques:
    - Direct similarity
    - Token overlap (handles "Arun Kumar" vs "Kumar Arun")
    - Initials matching
    """
    # Minimum length check - don't match fragments
    if len(name1) < 4 or len(name2) < 4:
        return False
    
    # Names should have at least 2 tokens to be matched (avoid "Kumar" matching with "Arun")
    tokens1 = name1.lower().split()
    tokens2 = name2.lower().split()
    
    if len(tokens1) < 2 or len(tokens2) < 2:
        return False
    
    # Direct similarity
    if _calculate_similarity(name1, name2) >= threshold:
        return True
    
    # Token-based matching (handle word order)
    if tokens1 and tokens2:
        overlap = len(set(tokens1) & set(tokens2)) / max(len(tokens1), len(tokens2))
        if overlap >= 0.7:  # 70% token overlap
            return True
    
    # Initials matching (A. Kumar vs Arun Kumar)
    def get_initials(name):
        return ''.join([word[0].upper() for word in name.split() if word])
    
    init1, init2 = get_initials(name1), get_initials(name2)
    if len(init1) > 1 and init1 == init2:
        return True
    
    return False


def normalize_entities(entities: Dict[str, List[Dict[str, Any]]], threshold: float = 0.85) -> Dict[str, Any]:
    """
    Normalize and deduplicate entities using fuzzy matching.
    
    Args:
        entities: Raw entities from entity_extractor
        threshold: Similarity threshold (0.85 = 85% similar)
    
    Returns:
        {
            "normalized": {category: [normalized entities]},
            "duplicates_found": [(original, canonical)],
            "conflicts": [conflict descriptions]
        }
    """
    normalized = defaultdict(list)
    duplicates_found = []
    conflicts = []
    
    # Track canonical names (first occurrence becomes canonical)
    canonical_map = {}  # original -> canonical
    
    for category, entity_list in entities.items():
        if not entity_list:
            continue
        
        seen_texts = {}  # canonical_text -> entity dict
        
        for entity in entity_list:
            text = entity.get("text", "").strip()
            if not text or len(text) < 2:
                continue
            
            # Find if this matches any existing canonical name
            matched_canonical = None
            for canonical_text in seen_texts.keys():
                if category == "persons" and _fuzzy_match_names(text, canonical_text, threshold):
                    matched_canonical = canonical_text
                    duplicates_found.append((text, canonical_text))
                    canonical_map[text] = canonical_text
                    break
                elif text.lower() == canonical_text.lower():
                    matched_canonical = canonical_text
                    break
            
            if matched_canonical:
                # Merge spans
                seen_texts[matched_canonical]["spans"].append(entity.get("span"))
                seen_texts[matched_canonical]["occurrences"] += 1
            else:
                # New canonical entity
                seen_texts[text] = {
                    "text": text,
                    "canonical": text,
                    "spans": [entity.get("span")],
                    "occurrences": 1,
                    "category": category
                }
                canonical_map[text] = text
        
        normalized[category] = list(seen_texts.values())
    
    # Detect role conflicts (same person in multiple roles)
    if "persons" in normalized:
        person_names = {p["canonical"]: p for p in normalized["persons"]}
        
        # Cross-check with role-specific categories (if they exist)
        # For now, just flag potential duplicates
        if len(duplicates_found) > 0:
            conflicts.append({
                "type": "name_variations",
                "message": f"Found {len(duplicates_found)} potential name variations that were normalized",
                "details": duplicates_found[:5]  # Show first 5
            })
    
    return {
        "normalized": dict(normalized),
        "duplicates_found": duplicates_found,
        "conflicts": conflicts,
        "canonical_map": canonical_map
    }


def detect_role_conflicts(entities: Dict[str, List[Dict[str, Any]]], evidence_text: str = "") -> List[Dict[str, Any]]:
    """
    Detect when the same person appears in conflicting roles.
    
    Examples:
    - "Police: Arun" and "Accused: Arun"
    - "Victim: Rahul" and "Witness: Rahul"
    
    Returns list of conflicts that need LLM resolution.
    """
    conflicts = []
    
    if not entities.get("persons"):
        return conflicts
    
    # Build a name index
    persons = entities["persons"]
    person_names = [p["text"] for p in persons]
    
    # Look for role keywords in evidence text
    role_patterns = {
        "police": ["police", "officer", "inspector", "constable", "sub-inspector", "PSI"],
        "accused": ["accused", "defendant", "respondent", "perpetrator", "culprit"],
        "victim": ["victim", "complainant", "injured", "deceased"],
        "witness": ["witness", "eye-witness", "eyewitness"],
    }
    
    # Extract person-role mappings from text
    person_roles = defaultdict(list)
    
    if evidence_text:
        lines = evidence_text.lower().split('\n')
        for line in lines:
            for person in person_names:
                person_lower = person.lower()
                if person_lower in line:
                    # Check which role keywords appear near this person
                    for role, keywords in role_patterns.items():
                        for keyword in keywords:
                            if keyword in line:
                                person_roles[person].append({
                                    "role": role,
                                    "context": line.strip()[:150]
                                })
                                break
    
    # Find conflicts: same person in multiple roles
    for person, roles in person_roles.items():
        unique_roles = set([r["role"] for r in roles])
        if len(unique_roles) > 1:
            conflicts.append({
                "person": person,
                "roles": list(unique_roles),
                "contexts": roles,
                "severity": "high" if {"police", "accused"}.issubset(unique_roles) else "medium",
                "requires_resolution": True
            })
    
    return conflicts
