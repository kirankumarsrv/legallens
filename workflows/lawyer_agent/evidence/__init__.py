"""
Evidence Ingestion Module

Handles loading, parsing, and extraction of user-uploaded case files.
Evidence lives in session state (not global DB).
"""

from .loader import load_evidence_files
from .parser import parse_evidence
from .entity_extractor import extract_entities

__all__ = ["load_evidence_files", "parse_evidence", "extract_entities"]
