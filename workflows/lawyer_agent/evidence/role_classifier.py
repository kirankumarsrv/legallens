"""
Role Classifier for Extracted Persons

Classifies extracted person entities into roles:
  - accused
  - complainant
  - witness
  - magistrate
  - investigator
  - advocate/lawyer
  - other

Uses hybrid approach:
  1. Regex patterns (high precision, offline)
  2. LLM (optional, for ambiguous cases)
"""

import re
from typing import List, Dict, Any, Optional


def _extract_context(person_name: str, text: str, window: int = 200) -> str:
    """Extract surrounding context for a person mention.

    Args:
        person_name: Name to search for
        text: Full evidence text
        window: Characters before/after to include

    Returns:
        Context snippet containing the person
    """
    pattern = re.escape(person_name)
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    if not matches:
        return ""

    # Get context from first mention
    m = matches[0]
    start = max(0, m.start() - window)
    end = min(len(text), m.end() + window)
    return text[start:end]


def _classify_by_regex(person_name: str, context: str, full_text: str) -> Optional[str]:
    """Classify role using regex patterns (high precision).

    Returns:
        Role string or None if pattern not matched
    """

    # Complainant patterns
    complainant_patterns = [
        r"complainant\s+(?:named|is)?\s*" + re.escape(person_name),
        r"petitioner\s+(?:named|is)?\s*" + re.escape(person_name),
        r"applicant\s+(?:named|is)?\s*" + re.escape(person_name),
        re.escape(person_name) + r"\s+(?:has|lodged|filed)\s+(?:a\s+)?(?:complaint|FIR)",
    ]

    for pattern in complainant_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            return "complainant"

    # Accused patterns
    accused_patterns = [
        r"accused\s+(?:named|is)?\s*" + re.escape(person_name),
        r"defendant\s+(?:named|is)?\s*" + re.escape(person_name),
        r"respondent\s+(?:named|is)?\s*" + re.escape(person_name),
        r"against\s+(?:the\s+)?accused\s+.*" + re.escape(person_name),
    ]

    for pattern in accused_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            return "accused"

    # Witness patterns
    witness_patterns = [
        r"witness\s+(?:named|is)?\s*" + re.escape(person_name),
        r"deposition\s+(?:by|of)\s+" + re.escape(person_name),
        r"examined\s+(?:the\s+)?witness\s+" + re.escape(person_name),
    ]

    for pattern in witness_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            return "witness"

    # Magistrate / Judge patterns
    magistrate_patterns = [
        r"(?:Magistrate|Judge|Justice)\s+(?:named|is)?\s*" + re.escape(person_name),
    ]

    for pattern in magistrate_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            return "magistrate"

    # Investigator / Officer patterns
    investigator_patterns = [
        r"(?:Inspector|Investigator|Officer)\s+(?:named|is)?\s*" + re.escape(person_name),
        re.escape(person_name) + r"\s+(?:investigated|inquired)",
    ]

    for pattern in investigator_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            return "investigator"

    # Advocate / Lawyer patterns
    advocate_patterns = [
        r"(?:Advocate|Lawyer|Counsel)\s+(?:for|of)?\s*" + re.escape(person_name),
        re.escape(person_name) + r"\s+(?:represented|counsel)",
    ]

    for pattern in advocate_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            return "advocate"

    return None


def classify_roles(
    entities: Dict[str, List[Dict[str, Any]]],
    evidence_text: str,
    llm_manager: Optional[Any] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Classify roles for extracted persons.

    Args:
        entities: Dict with 'persons' key containing list of {text, span} dicts
        evidence_text: Full evidence text to search for context
        llm_manager: Optional LLM manager for constrained LLM classification

    Returns:
        Updated entities dict with 'role' field added to each person
    """

    if "persons" not in entities:
        return entities

    # Classify each person
    for person_entry in entities["persons"]:
        person_name = person_entry["text"]

        # Try regex first (high precision, no API calls)
        role = _classify_by_regex(person_name, "", evidence_text)

        if role:
            person_entry["role"] = role
        else:
            # If regex fails and LLM available, use constrained prompt
            if llm_manager:
                context = _extract_context(person_name, evidence_text, window=150)
                role = _classify_with_llm(person_name, context, llm_manager)
                person_entry["role"] = role
            else:
                person_entry["role"] = "other"

    return entities


def _classify_with_llm(person_name: str, context: str, llm_manager: Any) -> str:
    """Use LLM to classify role (constrained, no hallucination).

    Args:
        person_name: Name of person to classify
        context: Text snippet containing the person
        llm_manager: LLM instance

    Returns:
        Role classification or 'other' if uncertain
    """

    prompt = f"""Classify the role of "{person_name}" based on this context:

{context}

Valid roles: accused, complainant, witness, magistrate, investigator, advocate, other

Return ONLY a JSON object with no extra text:
{{"role": "<one of the valid roles>"}}

If uncertain, return {{"role": "other"}}.
"""

    try:
        response = llm_manager.invoke(prompt)
        # Parse JSON response
        import json
        import re

        # Extract JSON from response
        match = re.search(r"\{.*?\}", response, re.DOTALL)
        if match:
            data = json.loads(match.group())
            role = data.get("role", "other")
            if role in [
                "accused",
                "complainant",
                "witness",
                "magistrate",
                "investigator",
                "advocate",
                "other",
            ]:
                return role
    except Exception as e:
        print(f"⚠️ LLM role classification failed for {person_name}: {e}")

    return "other"
