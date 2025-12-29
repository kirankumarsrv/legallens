"""
Cross-evidence contradiction detector

Compares extracted entities across multiple evidence files and flags
discrepancies (e.g., differing dates, FIR numbers, differing party names).

This module is conservative — it reports potential contradictions for
human review rather than making hard decisions.
"""
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
import re

from .entity_extractor import extract_entities


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return ""


def detect_contradictions(paths: List[Path]) -> List[Dict[str, Any]]:
    """Detect contradictions across a list of evidence file paths.

    Returns a list of contradiction records describing entity type,
    differing values and which files contain them.
    """
    if not paths:
        return []

    per_file_entities: List[Dict[str, List[Dict[str, Any]]]] = []
    for p in paths:
        text = ""
        if p.suffix.lower() in (".txt", ".md"):
            text = _read_text_file(p)
        else:
            # Try to use entity extractor on combined text; extractor's
            # TextExtractor fallback is handled elsewhere; here we keep simple
            text = _read_text_file(p)

        ents = extract_entities(text)
        per_file_entities.append({"path": str(p), "entities": ents})

    # Aggregate values per entity type across files
    agg = defaultdict(lambda: defaultdict(list))
    for file_entry in per_file_entities:
        path = file_entry["path"]
        ents = file_entry["entities"]
        for etype, items in ents.items():
            for item in items:
                # normalize simple textual value for matching
                val = re.sub(r"\s+", " ", item.get("text", "").strip())
                if val:
                    agg[etype][val].append(path)

    contradictions = []
    # For each entity type, if values are present in more than one distinct value, flag
    for etype, val_map in agg.items():
        if len(val_map) <= 1:
            continue

        # Build readable summary
        summary = {
            "entity_type": etype,
            "values": [],
        }
        for val, files in val_map.items():
            summary["values"].append({"value": val, "files": files})

        contradictions.append(summary)

    return contradictions
