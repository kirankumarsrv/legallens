"""
Evidence Parser

Extracts text from case files (PDFs, TXT, etc.).
Uses existing TextExtractor module.
"""

from pathlib import Path
from typing import List
from modules.text_extractor import TextExtractor

# Optional OCR imports
try:
    import pytesseract  # type: ignore
    from pdf2image import convert_from_path  # type: ignore
    from PIL import Image  # type: ignore
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False


def _ocr_image(path: Path) -> str:
    try:
        img = Image.open(path)
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


def _ocr_pdf(path: Path) -> str:
    texts = []
    try:
        # Allow explicit poppler path via env var for Windows users
        poppler_path = None
        from os import environ
        if environ.get("POPPLER_PATH"):
            poppler_path = environ.get("POPPLER_PATH")

        if poppler_path:
            pages = convert_from_path(str(path), poppler_path=poppler_path)
        else:
            pages = convert_from_path(str(path))
        # Allow explicit tesseract cmd if provided
        if environ.get("TESSERACT_CMD"):
            pytesseract.pytesseract.tesseract_cmd = environ.get("TESSERACT_CMD")

        for p in pages:
            texts.append(pytesseract.image_to_string(p))
    except Exception:
        return ""
    return "\n\n".join(texts)


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
                # If PDF text extraction yields very little, assume scanned PDF and try OCR
                if (not text or len(text.strip()) < 200) and OCR_AVAILABLE:
                    print(f"🔎 Low text from PDF; attempting OCR on {file.name}...")
                    ocr_text = _ocr_pdf(file)
                    if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        print(f"🖨️ OCR completed for {file.name} ({len(text)} chars)")
                    else:
                        print(f"   ⚠️ OCR did not improve extraction for {file.name}")
                texts.append(text)
                print(f"📄 Parsed PDF: {file.name} ({len(text)} chars)")
            elif file.suffix.lower() in [".txt", ".md"]:
                with open(file, "r", encoding="utf-8") as f:
                    text = f.read()
                texts.append(text)
                print(f"📋 Parsed text: {file.name} ({len(text)} chars)")
            elif file.suffix.lower() in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
                if OCR_AVAILABLE:
                    text = _ocr_image(file)
                    texts.append(text)
                    print(f"🖼️ OCR image: {file.name} ({len(text)} chars)")
                else:
                    print(f"⚠️  OCR libraries not available; cannot parse image: {file.name}")
            else:
                print(f"⚠️  Unsupported file type: {file.suffix}")
        except Exception as e:
            print(f"❌ Error parsing {file.name}: {str(e)}")
    
    if not texts:
        return ""
    
    combined = "\n\n--- NEXT DOCUMENT ---\n\n".join(texts)
    print(f"\n✅ Evidence parsing complete: {len(combined)} total chars")
    return combined
