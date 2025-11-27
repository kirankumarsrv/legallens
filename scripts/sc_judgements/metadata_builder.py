# modules/metadata_builder.py

"""
MetadataBuilder
---------------

Extracts structured metadata from unstructured Supreme Court judgment text.

Responsibilities (Algorithm Steps)
----------------------------------
1. Initialize LLM (through LLMManager)
2. Extract year from PDF path
3. Extract case name from first ~30 lines
4. Extract citations (AIR / SCC / SCR)
5. Summarize using LLMManager (first 5000 chars)
6. Return metadata dictionary

This class does *not* know about Groq or OpenAI directly.
All LLM logic is delegated to LLMManager.
"""

from __future__ import annotations
from typing import List, Optional


class MetadataBuilder:
    """
    Build structured metadata from extracted PDF text.

    Parameters
    ----------
    llm_manager : LLMManager
        An initialized LLMManager instance (Groq, OpenAI, etc.)
    """

    # ---------------------------------------------------------
    # STEP 1 — Initialize MetadataBuilder
    # ---------------------------------------------------------
    def __init__(self, llm_manager):
        self.llm = llm_manager

    # ---------------------------------------------------------
    # STEP 2 — Extract Year From PDF Path
    # ---------------------------------------------------------
    def extract_year(self, pdf_path: str) -> Optional[int]:
        """
        Extract year from folder name above PDF.

        Examples
        --------
        data/sc_judgments/1951/case.pdf  → 1951
        data/sc_judgments/abc/case.pdf  → None
        """
        try:
            # split path → take second last directory name
            year_str = pdf_path.replace("\\", "/").split("/")[-2]
            return int(year_str)
        except Exception:
            return None

    # ---------------------------------------------------------
    # STEP 3 — Extract Case Name
    # ---------------------------------------------------------
    def extract_case_name(self, text: str) -> Optional[str]:
        """
        Find case name using basic heuristics.

        Logic:
        - Look at first 30 lines
        - If line contains 'v.' or 'vs', assume it is a title line
        """
        lines = text.split("\n")[:30]
        for line in lines:
            clean = line.strip()
            if "v." in clean or "vs" in clean.lower():
                return clean
        return None

    # ---------------------------------------------------------
    # STEP 4 — Extract Citations (AIR / SCC / SCR)
    # ---------------------------------------------------------
    def extract_citations(self, text: str) -> List[str]:
        """
        Scan entire text for recognized citations.

        Returns first 10 citations max.
        """
        citations = []
        for line in text.split("\n"):
            clean = line.strip()
            if any(key in clean for key in ["AIR", "SCC", "SCR"]):
                citations.append(clean)

        return citations[:10]

    # ---------------------------------------------------------
    # STEP 5 — Summarize Text Using LLMManager
    # ---------------------------------------------------------
    def summarize(self, text: str) -> str:
        """
        Produce a 4–5 line legal summary using the chosen LLM.

        - Only first 5000 chars used for cost efficiency
        - LLMManager handles actual API details
        """
        sample = text[:5000]
        try:
            return self.llm.summarize(sample)
        except Exception as e:
            # If the LLM explodes (like my brain reading 600-page judgments)
            return f"[Summary unavailable: {str(e)}]"

    # ---------------------------------------------------------
    # STEP 6 — Build Final Metadata Dictionary
    # ---------------------------------------------------------
    def build_metadata(self, pdf_path: str, text: str) -> dict:
        """
        Combine all extracted metadata into one structured dictionary.
        """

        year = self.extract_year(pdf_path)
        case_name = self.extract_case_name(text)
        citations = self.extract_citations(text)
        summary = self.summarize(text)

        return {
            "pdf_path": pdf_path,
            "year": year,
            "case_name": case_name,
            "citations": citations,
            "summary": summary,
        }
