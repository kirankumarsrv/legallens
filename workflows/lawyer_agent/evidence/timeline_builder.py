"""
Timeline Builder for Legal Evidence

Constructs a chronological timeline from extracted dates and entities.
Links persons, locations, and events to specific dates.

Output: Ordered events with associated context (persons, locations, actions).
"""

import re
from typing import List, Dict, Any, Optional


def _parse_date(date_str: str) -> Optional[tuple]:
    """
    Parse various date formats and return (year, month, day) tuple for sorting.

    Supports: DD/MM/YYYY, DD-MM-YYYY, October 15 2024, July 2024
    """
    if not date_str:
        return None

    # Try DD/MM/YYYY or DD-MM-YYYY
    for sep in ["/", "-"]:
        if sep in date_str:
            parts = date_str.split(sep)
            if len(parts) == 3:
                try:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    # Normalize 2-digit years
                    if year < 100:
                        year = 2000 + year if year < 50 else 1900 + year
                    return (year, month, day)
                except ValueError:
                    pass

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    
    # Pattern: "month DD, YYYY" or "month DD YYYY"
    m = re.match(r"([a-z]{3})[a-z]*\s+(\d{1,2}),?\s+(\d{4})", date_str, re.IGNORECASE)
    if m:
        try:
            month_name, day, year = m.group(1).lower(), int(m.group(2)), int(m.group(3))
            month = month_map.get(month_name)
            if month:
                return (year, month, day)
        except ValueError:
            pass
    
    # Pattern: "month YYYY"
    m = re.match(r"([a-z]{3})[a-z]*\s+(\d{4})", date_str, re.IGNORECASE)
    if m:
        try:
            month_name, year = m.group(1).lower(), int(m.group(2))
            month = month_map.get(month_name)
            if month:
                return (year, month, 1)  # Default to 1st of month
        except ValueError:
            pass

    return None


def _extract_event_context(date_str: str, evidence_text: str, window: int = 300) -> str:
    """Extract the event/context surrounding a date mention.

    Args:
        date_str: Date string to search for
        evidence_text: Full evidence text
        window: Characters before/after to include

    Returns:
        Context snippet containing event description
    """
    pattern = re.escape(date_str)
    match = re.search(pattern, evidence_text, re.IGNORECASE)
    if not match:
        return ""

    start = max(0, match.start() - window)
    end = min(len(evidence_text), match.end() + window)
    context = evidence_text[start:end].strip()

    # Clean up: remove extra whitespace
    context = re.sub(r"\s+", " ", context)
    return context[:200]  # Limit to 200 chars


def _link_entities_to_date(
    date_str: str,
    context: str,
    entities: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[str]]:
    """Find entities mentioned near a date.

    Args:
        date_str: Date string
        context: Text context around the date
        entities: Extracted entities dict

    Returns:
        Dict with keys: persons, locations, sections mentioning this date
    """
    linked = {"persons": [], "locations": [], "sections": []}

    # Find persons mentioned in context
    for person_entry in entities.get("persons", []):
        if person_entry["text"].lower() in context.lower():
            role = person_entry.get("role", "")
            person_str = person_entry["text"]
            if role:
                person_str += f" ({role})"
            linked["persons"].append(person_str)

    # Find locations mentioned in context
    for loc_entry in entities.get("locations", []):
        if loc_entry["text"].lower() in context.lower():
            linked["locations"].append(loc_entry["text"])

    # Find sections mentioned in context
    for sec_entry in entities.get("sections", []):
        if sec_entry["text"] in context:
            linked["sections"].append(sec_entry["text"])

    return linked


def build_timeline(
    entities: Dict[str, List[Dict[str, Any]]],
    evidence_text: str,
) -> List[Dict[str, Any]]:
    """Build a chronological timeline from extracted entities and evidence.

    Args:
        entities: Extracted entities (must include 'dates')
        evidence_text: Full evidence text for context extraction

    Returns:
        List of timeline events, sorted chronologically:
        [
            {
                "date": "15/10/2024",
                "date_parsed": (2024, 10, 15),
                "event": "...",
                "persons": ["Rajesh Kumar (complainant)", ...],
                "locations": ["New Delhi", ...],
                "sections": ["354C", "406"],
            },
            ...
        ]
    """

    timeline = []

    if "dates" not in entities or not entities["dates"]:
        return timeline

    for date_entry in entities["dates"]:
        date_str = date_entry["text"]
        date_parsed = _parse_date(date_str)

        if not date_parsed:
            continue

        # Extract event context
        event = _extract_event_context(date_str, evidence_text)

        if not event:
            event = f"(Event on {date_str})"

        # Link entities to this date
        linked = _link_entities_to_date(date_str, event, entities)

        timeline.append(
            {
                "date": date_str,
                "date_parsed": date_parsed,
                "event": event,
                "persons": linked["persons"],
                "locations": linked["locations"],
                "sections": linked["sections"],
            }
        )

    # Sort by parsed date
    timeline.sort(key=lambda x: x["date_parsed"])

    return timeline
