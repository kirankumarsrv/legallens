# modules/legal_splitter.py

import re
import unicodedata
from typing import List, Dict



class LegalParagraphSplitter:
    """
    A robust paragraph + sentence-based text splitter for legal judgments.

    Features
    --------
    - Advanced PDF cleaning (ligatures, broken newlines, unicode normalization)
    - Detects real legal paragraphs
    - Merges tiny paragraphs
    - Splits long paragraphs into smaller chunks with overlap
    """

    def __init__(
        self,
        max_length: int = 900,
        min_length: int = 120,
        overlap: int = 80,
    ):
        self.max_length = max_length
        self.min_length = min_length
        self.overlap = overlap

    # ----------------------------------------------------
    # ADVANCED CLEANING (taken from your TextSplitter)
    # ----------------------------------------------------
    def _clean(self, text: str) -> str:
        """Clean noise and normalize legal PDF text."""

        # Remove carriage returns
        text = text.replace("\r", "")

        # Normalize unicode (NFKD)
        text = unicodedata.normalize("NFKD", text)

        # Fix common ligatures
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")

        # Remove non-printable characters
        text = "".join(ch for ch in text if ch.isprintable() or ch.isspace())

        # Remove hyphenated line breaks: "consti-\ntution"
        text = re.sub(r"-\n", "", text)

        # Random newlines inside paragraphs → convert to space
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        # Compress multiple spaces
        text = re.sub(r"\s{2,}", " ", text)

        # Restore paragraph breaks
        text = re.sub(r"\n\s*\n", "\n\n", text)

        # Normalize blank lines again
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    # ----------------------------------------------------
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs using real blank lines."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs

    # ----------------------------------------------------
    def _merge_small_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """Merge paragraphs shorter than min_length."""
        merged = []
        buffer = ""

        for p in paragraphs:
            if len(p) < self.min_length:
                buffer += " " + p
            else:
                if buffer:
                    merged.append(buffer.strip())
                    buffer = ""
                merged.append(p)

        if buffer:
            merged.append(buffer.strip())

        return merged

    # ----------------------------------------------------
    def _split_large_paragraph(self, text: str) -> List[str]:
        """Split very large paragraphs using overlap sliding window."""
        if len(text) <= self.max_length:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.max_length
            chunk = text[start:end]

            chunks.append(chunk)
            start = end - self.overlap

        return chunks

    # ----------------------------------------------------
    def split(self, text: str) -> List[str]:
        """
        Main function:
        1. clean
        2. paragraph split
        3. merge small
        4. split large
        """
        cleaned = self._clean(text)
        paragraphs = self._split_into_paragraphs(cleaned)
        paragraphs = self._merge_small_paragraphs(paragraphs)

        final_chunks = []
        for p in paragraphs:
            final_chunks.extend(self._split_large_paragraph(p))

        return final_chunks




class TextSplitter:
    """
    Smart text splitter optimized for legal judgments.

    Supports:
    - paragraph-based splitting
    - sentence-based splitting
    - token/char-length splitting (with overlap)
    """

    def __init__(self,
                 chunk_size: int = 1200,
                 chunk_overlap: int = 200,
                 mode: str = "paragraph"):
        """
        Parameters
        ----------
        chunk_size : int
            Maximum length of one chunk (characters).
        chunk_overlap : int
            Overlap between two consecutive chunks.
        mode : str
            "paragraph" | "sentence" | "char"
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.mode = mode

    # ----------------------------------------------
    # Cleaning
    # ----------------------------------------------
    def clean(self, text: str) -> str:
        """Clean noise and normalize whitespace."""
        text = text.replace("\r", "")
        text = re.sub(r"\n{2,}", "\n\n", text)      # collapse multiple newlines
        text = re.sub(r" +", " ", text)            # collapse spaces
        # Normalize unicode
        text = unicodedata.normalize("NFKD", text)

        # Fix common ligatures
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")

        # Remove non-printable characters
        text = "".join(ch for ch in text if ch.isprintable() or ch.isspace())

        # Fix hyphenated line breaks: "consti-\ntution" → "constitution"
        text = re.sub(r"-\n", "", text)

        # Remove random newlines inside sentences
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        # Collapse multiple spaces
        text = re.sub(r"\s{2,}", " ", text)

        # Restore paragraph breaks
        text = re.sub(r"\n\s*\n", "\n\n", text)

        return text.strip()
    
    
    # ----------------------------------------------
    # Paragraph Split
    # ----------------------------------------------
    def split_by_paragraph(self, text: str) -> List[str]:
        """Split text into paragraphs using blank lines."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs

    # ----------------------------------------------
    # Sentence Split
    # ----------------------------------------------
    def split_by_sentence(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    # ----------------------------------------------
    # Chunk Builder
    # ----------------------------------------------
    def build_chunks(self, units: List[str]) -> List[str]:
        """
        Merge units (sentences/paragraphs) into chunks
        that respect chunk_size and chunk_overlap.
        """
        chunks = []
        current = ""

        for u in units:
            if len(current) + len(u) + 1 <= self.chunk_size:
                current += " " + u if current else u
            else:
                chunks.append(current)
                # overlap logic
                current = current[-self.chunk_overlap:] + " " + u

        if current:
            chunks.append(current)

        return chunks

    # ----------------------------------------------
    # Master Split Function
    # ----------------------------------------------
    def split(self, text: str) -> List[Dict]:
        """
        Split text into structured chunks.

        Returns
        -------
        List[dict]
            Each chunk includes:
            - chunk_id
            - text
            - start_index
            - end_index
        """
        text = self.clean(text)

        if self.mode == "paragraph":
            units = self.split_by_paragraph(text)
        elif self.mode == "sentence":
            units = self.split_by_sentence(text)
        else:
            # pure char splitting
            units = [text[i:i + self.chunk_size]
                     for i in range(0, len(text), self.chunk_size)]

        chunks = self.build_chunks(units)

        # Build final structured chunks
        structured = []
        cursor = 0

        for i, ch in enumerate(chunks):
            start = text.find(ch, cursor)
            end = start + len(ch)
            cursor = end

            structured.append({
                "chunk_id": f"chunk_{i+1:05d}",
                "text": ch,
                "start_index": start,
                "end_index": end
            })

        return structured
