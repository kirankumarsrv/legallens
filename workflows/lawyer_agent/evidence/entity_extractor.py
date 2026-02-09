"""
Entity extractor for legal evidence

Hybrid approach: regex (high precision) + spaCy (fallback for names/places).
Enhanced for Indian legal documents with patterns for Indian names, locations, organizations.
Returns structured entities with basic provenance (text, spans).
"""
import re
from collections import defaultdict
from typing import List, Dict, Any, Set

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None


def _add_entity(entities: Dict[str, List[Dict[str, Any]]], key: str, text: str, span: tuple):
    """Add entity to collection, avoiding duplicates."""
    # Check if this entity already exists in the list
    for existing in entities[key]:
        if existing["text"].lower() == text.lower():
            return  # Skip duplicate
    entities[key].append({"text": text, "span": span})


def extract_entities(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """Extract legal entities from evidence text.

    Enhanced for Indian legal documents: person names, Indian locations, organizations.
    
    Returns a dict with keys: persons, organizations, locations, dates,
    sections, fir_numbers, case_numbers, authorities
    Each value is a list of {text, span} dicts.
    """
    if not text:
        return {}

    entities: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # Keep track of already-extracted spans to avoid duplicates
    extracted_spans: Set[tuple] = set()

    # Helper function to check for overlapping spans
    def span_overlaps(span: tuple) -> bool:
        for existing_span in extracted_spans:
            if (span[0] < existing_span[1] and span[1] > existing_span[0]):
                return True
        return False

    # Helper to safely add entity without overlaps
    def safe_add_entity(key: str, text: str, span: tuple):
        if not span_overlaps(span):
            _add_entity(entities, key, text, span)
            extracted_spans.add(span)

    # PASS 1: REGEX-BASED HIGH-PRECISION PATTERNS
    # ==============================================

    # IPC/CrPC/Section references
    for m in re.finditer(r"\b(?:Section|Sec\.?|S\.)\s*(\d{1,3}[A-Za-z]?(?:\-[A-Za-z0-9]+)?)\b", text, flags=re.IGNORECASE):
        section = m.group(1).strip()
        if section and not section.isalpha():
            safe_add_entity("sections", section, m.span())

    # FIR / FIR No patterns
    for m in re.finditer(r"\bFIR\b\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d{2,4})", text, flags=re.IGNORECASE):
        safe_add_entity("fir_numbers", m.group(1), m.span())

    # Case / Charge sheet numbers
    for m in re.finditer(r"\b(?:Case|Charge\s+Sheet|CS)\b\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d{2,4})", text, flags=re.IGNORECASE):
        case_num = m.group(1).strip()
        if case_num:
            safe_add_entity("case_numbers", case_num, m.span())

    # Dates (DD/MM/YYYY or DD-MM-YYYY format)
    for m in re.finditer(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text):
        safe_add_entity("dates", m.group(0), m.span())

    # Alternative date formats
    for m in re.finditer(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b", text, flags=re.IGNORECASE):
        safe_add_entity("dates", m.group(0), m.span())
    
    for m in re.finditer(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}\b", text, flags=re.IGNORECASE):
        safe_add_entity("dates", m.group(0), m.span())
    
    for m in re.finditer(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b", text, flags=re.IGNORECASE):
        safe_add_entity("dates", m.group(0), m.span())

    # Authorities (Police Station, Court, etc.)
    for m in re.finditer(r"(?:Police Station|Court|Magistrate|Cyber Crime Cell)\s*[:\-]?\s*([A-Z][A-Za-z\s,&.]*?)(?:\n|FIR|$)", text, flags=re.IGNORECASE):
        authority_name = m.group(1).strip()
        if authority_name and len(authority_name) > 2 and not authority_name.startswith(","):
            safe_add_entity("authorities", authority_name, m.span())

    # PASS 2: ENHANCED REGEX FOR INDIAN NAMES & LOCATIONS
    # =====================================================
    
    # Person references from common role patterns (e.g., "Officer Arun Kumar", "Accused: Munjappa")
    # This captures names after role indicators
    role_patterns = [
        r"(?:Accused|Accused is|Accused:|Perpetrator|Suspect)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:Complainant|Witness|Officer|Police Officer|Constable|Inspector|Magistrate)[\s:]*(?:named|is)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:Shop Owner|Manager|Security Officer|CCTV Operator)[\s:]*(?:named)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        r"(?:also known as|also referred as|alias)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"(?:Key Persons?|Persons? Involved)[\s:]*-\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
    ]
    
    for pattern in role_patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            name = m.group(1).strip()
            if name and len(name.split()) >= 1:  # At least first name
                safe_add_entity("persons", name, m.span())

    # Capitalized name patterns (any sequence of 1-4 capitalized words separated by space)
    # This is more aggressive - catches names in bullet points and sentences
    prepositions = {'at', 'in', 'from', 'by', 'or', 'and', 'the', 'a', 'to', 'for', 'of', 'with', 'on', 'as', 'is', 'be'}
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", text):
        name = m.group(1).strip()
        first_word = name.split()[0].lower()
        
        # Filter out false positives
        false_positives = {'The', 'This', 'That', 'Police', 'Court', 'FIR', 'Section', 'IPC', 'CrPC', 'Age', 'DOB', 'ID', 'Resident', 'Witness', 'Officer', 'Accused', 'Complainant', 'Shop', 'Mall', 'Hospital', 'Store', 'CCTV', 'Video', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'At', 'In', 'From', 'By', 'Or', 'And', 'A', 'To', 'For', 'Of', 'With', 'On', 'As', 'Is', 'Be', 'Electronic', 'Rs', 'Kiosk'}
        
        # Skip prepositions at the start
        if first_word in prepositions or name in false_positives:
            continue
        
        if len(name.split()) in (2, 3, 4):  # Likely a person name (2-4 words)
            safe_add_entity("persons", name, m.span())

    # Location patterns: cities, streets, malls, hospitals, places
    location_patterns = [
        r"(?:at|in|from|near)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Mall|Hospital|Complex|Lane|Street|Road|Station|Building|Centre|Center)))",
        r"(?:Resident of|Located at|Address:)[\s:]*([A-Za-z0-9\s,.]+ (?:Lane|Street|Road|Avenue|Boulevard|Plaza))",
        r"\b([A-Z][a-z]+(?:(?:a|pur|ganj|bazaar|nagar|ward)))\b",  # Common Indian place name endings
    ]
    
    for pattern in location_patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            location = m.group(1).strip()
            if location and len(location) > 2:
                safe_add_entity("locations", location, m.span())

    # Known Indian city names and common mall/hospital/place suffixes
    indian_places = [
        "Bangalore", "Bengaluru", "Delhi", "Mumbai", "Pune", "Chennai", "Kolkata",
        "Hyderabad", "Ahmedabad", "Lucknow", "Chandigarh", "Indore", "Jaipur",
        "Central Shopping Mall", "Apollo Hospital", "City Centre", "Shopping Complex"
    ]
    for place in indian_places:
        for m in re.finditer(re.escape(place), text, flags=re.IGNORECASE):
            safe_add_entity("locations", place, m.span())

    # Organization patterns (malls, hospitals, police departments, shops, stores)
    org_patterns = [
        r"\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\s+(?:Mall|Hospital|Police|Department|Centre|Center|Complex|Store|Shop|Bank|Office))\b",
        r"(?:at|from)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Store|Shop|Kiosk|Counter)))",
    ]
    
    for pattern in org_patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            org = m.group(1).strip()
            if org and len(org) > 3:
                safe_add_entity("organizations", org, m.span())

    # PASS 3: spaCy-based NER (FALLBACK)
    # ==================================
    if _nlp:
        doc = _nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                safe_add_entity("persons", ent.text, (ent.start_char, ent.end_char))
            elif ent.label_ in ("GPE", "LOC"):
                safe_add_entity("locations", ent.text, (ent.start_char, ent.end_char))
            elif ent.label_ in ("ORG",):
                safe_add_entity("organizations", ent.text, (ent.start_char, ent.end_char))
            elif ent.label_ == "DATE":
                safe_add_entity("dates", ent.text, (ent.start_char, ent.end_char))

    # Convert defaultdict -> dict
    return {k: v for k, v in entities.items()}
