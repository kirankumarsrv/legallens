"""
Entity extraction node for the Lawyer Agent workflow (LLM-Based NER).

Extracts structured entities from `state['evidence_text']` using LLM instead of regex.
Stores them in `state['entities']`.
"""
import json
from workflows.lawyer_agent.state import LawyerState


def entity_extraction_node(state: LawyerState, llm=None) -> LawyerState:
    """Populate `state['entities']` from evidence_text using LLM.

    If no evidence_text is present, try to use the problem statement (question).
    If neither is available, set entities to {}.
    """
    print("\n🔎 PHASE: Entity Extraction (LLM-Based NER)")
    
    # Try to get evidence text from evidence files, or fall back to problem statement
    text_to_extract = state.get("evidence_text") or state.get("question") or ""
    
    if not text_to_extract:
        print("   ⚠️  No evidence text or problem statement available.")
        print("       Make sure to click 'Save Problem' before clicking 'Run Compute'")
        state["entities"] = {}
        return state

    # Show what we're extracting from
    if state.get("evidence_text"):
        print(f"   📄 Extracting from uploaded evidence files ({len(state['evidence_text'])} chars)")
    else:
        print(f"   📝 Extracting from problem statement ({len(text_to_extract)} chars)")

    # Extract entities using LLM
    entities = _extract_entities_with_llm(text_to_extract, llm)
    state["entities"] = entities

    if state.get("reasoning_trace") is None:
        state["reasoning_trace"] = []

    total_entities = sum(len(v) for v in entities.values())
    state["reasoning_trace"].append(f"ENTITY EXTRACTION (LLM): found {total_entities} entities")
    entity_types = ', '.join([k for k,v in entities.items() if v])
    print(f"   ✅ Extracted {total_entities} entities: {entity_types}")

    return state


def _extract_entities_with_llm(text: str, llm) -> dict:
    """
    Use LLM to extract entities from text in Indian legal context.
    
    Returns:
        Dictionary with entity categories and extracted entities
    """
    if not llm:
        print("   ⚠️  No LLM provided, returning empty entities")
        return {
            "persons": [],
            "dates": [],
            "sections": [],
            "case_numbers": [],
            "locations": [],
            "organizations": [],
            "authorities": [],
            "amounts": []
        }
    
    prompt = f"""Extract entities from this Indian legal case text. Return ONLY valid JSON with these exact keys:

{{
  "persons": ["full names of people mentioned"],
  "dates": ["dates in natural format"],
  "sections": ["IPC/CrPC/law sections like '379', '380'"],
  "case_numbers": ["FIR numbers, case numbers"],
  "locations": ["places, addresses, cities"],
  "organizations": ["companies, hospitals, malls, shops"],
  "authorities": ["police stations, courts"],
  "amounts": ["monetary values mentioned"]
}}

Rules:
- Extract FULL names (e.g., "Arun Kumar Singh", not just "Arun")
- Keep name variations separate (e.g., "Munjappa" and "Munyappa" are different for now)
- Include role context if useful (e.g., "Police Officer Arun Kumar", "Accused Munjappa")
- Extract ALL mentions, even duplicates - we'll normalize later
- For sections, extract only the number (e.g., "379" from "Section 379 IPC")
- Return empty arrays [] if no entities found in a category

Text:
{text[:8000]}

JSON Output:"""

    try:
        response = llm.generate(prompt, temperature=0.0, max_tokens=2000)
        
        # Parse JSON response
        # Try to extract JSON from markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        entities = json.loads(response.strip())
        
        # Validate structure
        required_keys = ["persons", "dates", "sections", "case_numbers", "locations", "organizations", "authorities", "amounts"]
        for key in required_keys:
            if key not in entities:
                entities[key] = []
        
        return entities
        
    except Exception as e:
        print(f"   ❌ LLM entity extraction failed: {e}")
        # Return empty structure
        return {
            "persons": [],
            "dates": [],
            "sections": [],
            "case_numbers": [],
            "locations": [],
            "organizations": [],
            "authorities": [],
            "amounts": []
        }
