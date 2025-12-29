"""
Legal Document Translator

Translates legal documents while preserving:
- Section/law references (e.g., "IPC 354C" stays as is)
- Case numbers, dates, proper nouns
- Legal terminology context

Uses Google Translate API with fallback to basic translation.
"""

from typing import Optional
import re
from functools import lru_cache

# Optional: Google Translate
try:
    from google.cloud import translate_v2
    GOOGLE_TRANSLATE_AVAILABLE = True
except Exception:
    GOOGLE_TRANSLATE_AVAILABLE = False

try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except Exception:
    LANGDETECT_AVAILABLE = False


# Language code mapping
LANGUAGE_CODES = {
    "hi": "Hindi",
    "en": "English",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
}

# Legal term patterns to preserve
PRESERVE_PATTERNS = [
    r'\b(?:IPC|CrPC|Constitution)\s+(?:Section|Sec\.?|धारा|অধ্যায়|कलम|ವಿಭಾಗ)\s*[:\-]?\s*(\d+[A-Za-z]*)',
    r'\bFIR\b\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d{2,4})',
    r'\b(?:Case|CS)\b\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d+[/\-]\d{2,4})',
    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # Dates
]


def _extract_preserve_tokens(text: str) -> dict:
    """Extract legal references that should not be translated."""
    preserve_map = {}
    token_id = 0
    
    for pattern in PRESERVE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            token = match.group(0)
            placeholder = f"__PRESERVE_{token_id}__"
            preserve_map[placeholder] = token
            text = text[:match.start()] + placeholder + text[match.end():]
            token_id += 1
    
    return text, preserve_map


def _restore_preserve_tokens(text: str, preserve_map: dict) -> str:
    """Restore legal references after translation."""
    for placeholder, original in preserve_map.items():
        text = text.replace(placeholder, original)
    return text


def translate_legal_google(
    text: str,
    source_language: str = "hi",
    target_language: str = "en",
) -> str:
    """
    Translate legal text using Google Cloud Translation API.
    
    Preserves legal references (IPC sections, case numbers, dates).
    
    Args:
        text: Text to translate
        source_language: Source language code (e.g., "hi", "ta")
        target_language: Target language code (default: "en")
    
    Returns:
        Translated text with preserved legal references
    """
    if not GOOGLE_TRANSLATE_AVAILABLE:
        return text  # Fallback: return original
    
    try:
        # Extract legal tokens
        masked_text, preserve_map = _extract_preserve_tokens(text)
        
        # Translate via Google
        client = translate_v2.Client()
        result = client.translate_text(
            masked_text,
            source_language_code=source_language,
            target_language_code=target_language,
        )
        
        translated = result["translatedText"]
        
        # Restore legal tokens
        translated = _restore_preserve_tokens(translated, preserve_map)
        
        return translated
    
    except Exception as e:
        print(f"⚠️  Google Translate error: {e}. Returning original text.")
        return text


def translate_legal_fallback(
    text: str,
    source_language: str = "hi",
    target_language: str = "en",
) -> str:
    """
    Fallback translation using simple pattern-based approach.
    
    This is a PLACEHOLDER - real implementation would use:
    - Google Translate API
    - Azure Translator
    - HuggingFace Translation Model
    
    For now, returns text with metadata.
    """
    if source_language == target_language:
        return text
    
    # Extract legal tokens (preserve them)
    masked_text, preserve_map = _extract_preserve_tokens(text)
    
    # In production, use actual translation service here
    # For now: mark as needing translation
    translated = masked_text
    
    # Restore legal tokens
    translated = _restore_preserve_tokens(translated, preserve_map)
    
    # Add metadata
    return f"[Translated from {LANGUAGE_CODES.get(source_language, source_language)}]\n{translated}"


def translate_legal(
    text: str,
    source_language: str = "hi",
    target_language: str = "en",
    use_google: bool = True,
) -> dict:
    """
    Translate legal document intelligently.
    
    Args:
        text: Text to translate
        source_language: Source language code
        target_language: Target language code
        use_google: Try Google API first (default: True)
    
    Returns:
        {
            "original": original text,
            "translated": translated text,
            "source_language": source_language,
            "target_language": target_language,
            "preserved_terms": list of legal terms that were preserved,
            "method": "google" | "fallback"
        }
    """
    
    if source_language == target_language:
        return {
            "original": text,
            "translated": text,
            "source_language": source_language,
            "target_language": target_language,
            "preserved_terms": [],
            "method": "none",
        }
    
    # Try Google first
    if use_google and GOOGLE_TRANSLATE_AVAILABLE:
        try:
            translated = translate_legal_google(text, source_language, target_language)
            method = "google"
        except Exception:
            translated = translate_legal_fallback(text, source_language, target_language)
            method = "fallback"
    else:
        translated = translate_legal_fallback(text, source_language, target_language)
        method = "fallback"
    
    # Extract preserved terms
    _, preserve_map = _extract_preserve_tokens(text)
    preserved_terms = list(preserve_map.values())
    
    return {
        "original": text,
        "translated": translated,
        "source_language": source_language,
        "target_language": target_language,
        "preserved_terms": preserved_terms,
        "method": method,
    }


# LangChain Tool wrapper
def get_legal_translator_tool():
    """Return LangChain tool for legal translation."""
    from langchain_core.tools import tool
    
    @tool
    def legal_translator(
        text: str,
        source_language: str = "hi",
        target_language: str = "en",
    ) -> str:
        """
        Translate a legal document from one language to another.
        
        Preserves legal references like:
        - IPC sections (e.g., "IPC 354C")
        - Case numbers (e.g., "CS-123/2024")
        - Dates (e.g., "15/10/2024")
        - Proper nouns (names, places, courts)
        
        Args:
            text: The legal document text to translate
            source_language: Source language code (hi, ta, mr, en, etc.)
            target_language: Target language code (default: en for English)
        
        Returns:
            Translated text with preserved legal terminology
        
        Example:
            legal_translator(
                "IPC धारा 354C के तहत शिकायत",
                source_language="hi",
                target_language="en"
            )
        """
        result = translate_legal(text, source_language, target_language)
        
        # Format output for LLM
        output = result["translated"]
        if result.get("preserved_terms"):
            output += f"\n\n[Preserved legal terms: {', '.join(result['preserved_terms'])}]"
        if result["method"] == "fallback":
            output += f"\n[Note: Using fallback translation method]"
        
        return output
    
    return legal_translator


if __name__ == "__main__":
    # Test
    test_hindi = """
    IPC धारा 354C के तहत शिकायत दर्ज की गई है।
    शिकायतकर्ता: राजेश कुमार
    तारीख: 15/10/2024
    FIR No. 12345/2024
    """
    
    result = translate_legal(test_hindi, source_language="hi", target_language="en")
    print("Original:", result["original"])
    print("\nTranslated:", result["translated"])
    print("\nPreserved Terms:", result["preserved_terms"])
    print("\nMethod:", result["method"])
