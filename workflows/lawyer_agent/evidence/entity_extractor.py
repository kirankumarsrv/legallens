"""
Entity extractor for legal evidence

Hybrid approach: regex (high precision) + spaCy (names/places).
Returns structured entities with basic provenance (text, spans).
"""
import re
from collections import defaultdict
from typing import List, Dict, Any

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None


def _add_entity(entities: Dict[str, List[Dict[str, Any]]], key: str, text: str, span: tuple):
    entities[key].append({"text": text, "span": span})


def extract_entities(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """Extract legal entities from evidence text.

    Returns a dict with keys: persons, organizations, locations, dates,
    sections, fir_numbers, case_numbers, authorities
    Each value is a list of {text, span} dicts.
    """
    if not text:
        return {}

    entities: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # -----------------------------
    # Regex-based high-precision patterns
    # -----------------------------
    # IPC/CrPC/Section references (captures numeric and alphanumeric like 354C, 406, 503)
    # More precise: must start with 1-3 digits, optionally followed by a-z (like 354C, not just "C")
    for m in re.finditer(r"\b(?:Section|Sec\.?|S\.)\s*(\d{1,3}[A-Za-z]?(?:\-[A-Za-z0-9]+)?)\b", text, flags=re.IGNORECASE):
        section = m.group(1).strip()
        if section and not section.isalpha():  # Ensure it has at least a digit
            _add_entity(entities, "sections", section, m.span())

    # FIR / FIR No / FIR Number patterns
    # Matches patterns like "FIR 12345/2024" or "FIR No. 12345/2024"
    # Requires digits and forward slash format
    for m in re.finditer(r"\bFIR\b\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d{2,4})", text, flags=re.IGNORECASE):
        _add_entity(entities, "fir_numbers", m.group(1), m.span())

    # Case / Charge sheet numbers (common formats like "CS-789/2024" or "Case 123/2024")
    # More restrictive: requires digits followed by optional dash/slash and more digits
    for m in re.finditer(r"\b(?:Case|Charge\s+Sheet|CS)\b\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d{2,4})", text, flags=re.IGNORECASE):
        case_num = m.group(1).strip()
        if case_num:
            _add_entity(entities, "case_numbers", case_num, m.span())

    # Dates (DD/MM/YYYY or DD-MM-YYYY format)
    for m in re.finditer(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text):
        _add_entity(entities, "dates", m.group(0), m.span())

    # Alternative date formats
    # Format 1: "15 October 2024" or "15 Oct 2024"
    for m in re.finditer(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b", text, flags=re.IGNORECASE):
        _add_entity(entities, "dates", m.group(0), m.span())
    
    # Format 2: "October 15, 2024" or "Oct 15, 2024"
    for m in re.finditer(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}\b", text, flags=re.IGNORECASE):
        _add_entity(entities, "dates", m.group(0), m.span())
    
    # Format 3: "July 2024" or "October 2024" (month year only)
    for m in re.finditer(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b", text, flags=re.IGNORECASE):
        _add_entity(entities, "dates", m.group(0), m.span())

    # Authorities (Police Station, Court, etc.) - capture location name only
    # Matches "Police Station: CityName" and extracts just the location part
    # Requires at least 3 chars to avoid single words
    for m in re.finditer(r"(?:Police Station|Court|Magistrate|Cyber Crime Cell)\s*[:\-]?\s*([A-Z][A-Za-z\s,&.]*?)(?:\n|FIR|$)", text, flags=re.IGNORECASE):
        authority_name = m.group(1).strip()
        if authority_name and len(authority_name) > 2 and not authority_name.startswith(","):
            _add_entity(entities, "authorities", authority_name, m.span())

    # -----------------------------
    # spaCy-based NER for persons, orgs, GPE
    # -----------------------------
    if _nlp:
        doc = _nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                _add_entity(entities, "persons", ent.text, (ent.start_char, ent.end_char))
            elif ent.label_ in ("GPE", "LOC"):
                _add_entity(entities, "locations", ent.text, (ent.start_char, ent.end_char))
            elif ent.label_ in ("ORG",):
                _add_entity(entities, "organizations", ent.text, (ent.start_char, ent.end_char))
            elif ent.label_ == "DATE":
                _add_entity(entities, "dates", ent.text, (ent.start_char, ent.end_char))

    # Convert defaultdict -> dict
    return {k: v for k, v in entities.items()}
