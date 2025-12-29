"""
Evidence Parser

Extracts text from case files (PDFs, TXT, etc.).
Uses existing TextExtractor module.
"""

from pathlib import Path
from typing import List
from modules.text_extractor import TextExtractor


def parse_evidence(files: List[Path]) -> str:
    """
    Parse evidence files and extract text content.
    
    Args:
        files: List of Path objects to parse
        
    Returns:
        Concatenated text from all files
    """
    if not files:
        return ""
    
    extractor = TextExtractor()
    texts = []
    
    for file in files:
        try:
            if file.suffix.lower() == ".pdf":
                text = extractor.extract_pdf(str(file))
                texts.append(text)
                print(f"📄 Parsed PDF: {file.name} ({len(text)} chars)")
            elif file.suffix.lower() in [".txt", ".md"]:
                with open(file, "r", encoding="utf-8") as f:
                    text = f.read()
                texts.append(text)
                print(f"📋 Parsed text: {file.name} ({len(text)} chars)")
            else:
                print(f"⚠️  Unsupported file type: {file.suffix}")
        except Exception as e:
            print(f"❌ Error parsing {file.name}: {str(e)}")
    
    if not texts:
        return ""
    
    combined = "\n\n--- NEXT DOCUMENT ---\n\n".join(texts)
    print(f"\n✅ Evidence parsing complete: {len(combined)} total chars")
    return combined
