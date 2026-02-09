"""
Entity Normalization Node (LLM-Based Anomaly Detection)

Processes extracted entities using LLM to:
1. Normalize name variations
2. Detect anomalies (role conflicts, ambiguities, inconsistencies)
3. Generate clarification questions for lawyer
"""

import json
from workflows.lawyer_agent.state import LawyerState


def entity_normalization_node(
    state: LawyerState,
    llm=None,
    auto_resolve: bool = False,
    similarity_threshold: float = 0.85
) -> LawyerState:
    """
    Normalize entities and detect anomalies using LLM.
    
    Args:
        state: Current state with entities
        llm: LLM for normalization and anomaly detection
        auto_resolve: If True, auto-resolve high-confidence conflicts
        similarity_threshold: Not used in LLM approach
    
    Outputs to state:
        - normalized_entities: Deduplicated entities
        - entity_canonical_map: Name variation mappings
        - entity_conflicts: Detected anomalies
        - entity_clarifications: Questions for lawyer
        - entity_summary: Human-readable summary
    """
    print("\n🔄 ENTITY NORMALIZATION & CONFLICT DETECTION (LLM-Based)")
    
    entities = state.get("entities", {})
    if not entities or not any(entities.values()):
        print("   ℹ️  No entities to normalize; skipping.")
        print("       (This usually means entity extraction didn't find any entities)")
        state["normalized_entities"] = {}
        state["entity_conflicts"] = []
        state["entity_clarifications"] = []
        state["entity_canonical_map"] = {}
        state["entity_summary"] = "No entities extracted."
        return state
    
    if not llm:
        print("   ⚠️  No LLM available; returning raw entities without normalization")
        state["normalized_entities"] = entities
        state["entity_conflicts"] = []
        state["entity_clarifications"] = []
        state["entity_canonical_map"] = {}
        state["entity_summary"] = "Entities extracted but not normalized (no LLM)"
        return state
    
    # Use LLM to normalize entities and detect anomalies
    print("   1️⃣  Normalizing entities and detecting anomalies with LLM...")
    evidence_text = state.get("evidence_text", "") or state.get("question", "")
    
    result = _normalize_and_detect_anomalies_with_llm(entities, evidence_text, llm)
    
    # Show results
    duplicates_count = len(result.get("name_variations", []))
    conflicts_count = len(result.get("anomalies", []))
    
    if duplicates_count > 0:
        print(f"   ✅ Found and merged {duplicates_count} name variations")
        for variation in result["name_variations"][:3]:
            print(f"      • '{variation['variation']}' → '{variation['canonical']}'")
    
    if conflicts_count > 0:
        print(f"   ⚠️  Found {conflicts_count} anomalies requiring clarification")
        for anomaly in result["anomalies"][:3]:
            severity = anomaly.get("severity", "MEDIUM")
            print(f"      • [{severity}] {anomaly.get('description', 'Unknown anomaly')[:80]}")
    
    # Generate clarification questions for lawyer
    clarification_questions = [
        {
            "id": str(idx + 1),  # Store as string for API compatibility
            "person": anomaly.get("entity", "Unknown"),
            "question": anomaly.get("clarification_question", "Please review this entity"),
            "context": anomaly.get("description", ""),
            "severity": anomaly.get("severity", "MEDIUM"),
            "answered": False  # Initially unanswered
        }
        for idx, anomaly in enumerate(result.get("anomalies", []))
    ]
    
    # Generate summary
    entity_summary = f"""Entity Extraction & Normalization Summary:
- Total entities: {sum(len(v) for v in result['normalized_entities'].values())}
- Name variations merged: {duplicates_count}
- Anomalies detected: {conflicts_count}
- Clarifications needed: {len(clarification_questions)}
"""
    
    # Update state
    state["normalized_entities"] = result["normalized_entities"]
    state["entity_canonical_map"] = result.get("canonical_map", {})
    state["entity_conflicts"] = result.get("anomalies", [])
    state["entity_clarifications"] = clarification_questions
    state["entity_summary"] = entity_summary
    
    # Audit trail
    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []
    
    state["reasoning_trace"].append(
        f"ENTITY NORMALIZATION (LLM): Merged {duplicates_count} variations, "
        f"detected {conflicts_count} anomalies, "
        f"{len(clarification_questions)} clarifications needed"
    )
    
    print(f"   ✅ Entity normalization complete")
    
    return state


def _normalize_and_detect_anomalies_with_llm(entities: dict, evidence_text: str, llm) -> dict:
    """
    Use LLM to normalize entities and detect anomalies in one pass.
    
    Returns:
        Dictionary with:
        - normalized_entities: Deduplicated entities
        - name_variations: List of name variations found
        - canonical_map: Mapping from variations to canonical names
        - anomalies: List of detected anomalies with severity and questions
    """
    
    prompt = f"""Analyze these extracted entities and the original text to:
1. Normalize name variations (e.g., "Munjappa" and "Munyappa" are the same)
2. Detect anomalies (role conflicts, ambiguities, inconsistencies)

ENTITIES EXTRACTED:
{json.dumps(entities, indent=2)}

ORIGINAL TEXT:
{evidence_text[:6000]}

Return ONLY valid JSON with this structure:

{{
  "normalized_entities": {{
    "persons": ["canonical names after merging variations"],
    "dates": ["normalized dates"],
    "sections": ["deduplicated sections"],
    "case_numbers": ["unique case numbers"],
    "locations": ["unique locations"],
    "organizations": ["unique organizations"],
    "authorities": ["unique authorities"],
    "amounts": ["unique amounts"]
  }},
  "name_variations": [
    {{"variation": "Munyappa", "canonical": "Munjappa", "reason": "Spelling variation, 88% similarity"}}
  ],
  "canonical_map": {{
    "Munyappa": "Munjappa",
    "Original Name": "Canonical Name"
  }},
  "anomalies": [
    {{
      "type": "ROLE_CONFLICT|NAME_AMBIGUITY|INCONSISTENCY|DUPLICATE",
      "severity": "HIGH|MEDIUM|LOW",
      "entity": "Person/Location/etc name",
      "description": "Brief description of the anomaly",
      "clarification_question": "Question to ask the lawyer"
    }}
  ]
}}

ANOMALY DETECTION RULES:
- ROLE_CONFLICT: Same person with different/contradictory roles (e.g., both complainant AND police officer)
- NAME_AMBIGUITY: Same first name, different last name or missing last name (e.g., "Priya Sharma" vs "Priya")
- INCONSISTENCY: Same entity with conflicting attributes (different ages, addresses, etc.)
- DUPLICATE: Clear duplicate that should be merged

Mark severity based on impact:
- HIGH: Critical conflicts affecting case validity
- MEDIUM: Ambiguities needing clarification
- LOW: Minor duplicates/variations

Return empty arrays [] if none found in a category.

JSON Output:"""

    try:
        response = llm.generate(prompt, temperature=0.0, max_tokens=3000)
        
        # Parse JSON response
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response.strip())
        
        # Validate structure
        if "normalized_entities" not in result:
            result["normalized_entities"] = entities
        if "name_variations" not in result:
            result["name_variations"] = []
        if "canonical_map" not in result:
            result["canonical_map"] = {}
        if "anomalies" not in result:
            result["anomalies"] = []
        
        return result
        
    except Exception as e:
        print(f"   ❌ LLM normalization failed: {e}")
        # Return raw entities without normalization
        return {
            "normalized_entities": entities,
            "name_variations": [],
            "canonical_map": {},
            "anomalies": []
        }
