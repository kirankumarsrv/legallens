"""
Language Detection and Routing for Multilingual Legal Documents

Detects the language of evidence and tracks it through the workflow.
"""

from typing import Optional, Tuple
from pathlib import Path

# Language mapping
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
}

LANGUAGE_CODES = {v: k for k, v in LANGUAGE_NAMES.items()}


def detect_language(text: str) -> Optional[str]:
    """
    Detect language of text.
    
    Args:
        text: Text to detect language from
    
    Returns:
        Language code (e.g., "hi", "ta", "en") or None if detection fails
    """
    if not text or len(text.strip()) < 10:
        return None
    
    try:
        from langdetect import detect, LangDetectException
        
        # Try to detect
        lang_code = detect(text)
        
        # Map to our standard codes
        if lang_code in LANGUAGE_NAMES:
            return lang_code
        
        # Fallback mapping for common codes
        mapping = {
            "hi": "hi",  #Hindi
            "ta": "ta",  # Tamil
            "mr": "mr",  # Marathi
            "te": "te",  # Telugu
            "kn": "kn",  # Kannada
            "ml": "ml",  # Malayalam
            "bn": "bn",  # Bengali
            "gu": "gu",  # Gujarati
            "en": "en",  # English
            "pa": "pa",  # Punjabi
            "ur": "ur",  # Urdu
        }
        
        return mapping.get(lang_code)
    
    except Exception:
        return None


def detect_language_with_confidence(text: str) -> dict:
    """
    Detect language with confidence scores.
    
    Returns:
        {
            "primary_language": "hi",
            "primary_language_name": "Hindi",
            "confidence": 0.85,
            "detected_languages": {"hi": 0.85, "mr": 0.10, "en": 0.05}
        }
    """
    if not text or len(text.strip()) < 10:
        return {
            "primary_language": None,
            "primary_language_name": None,
            "confidence": 0.0,
            "detected_languages": {},
        }
    
    try:
        from langdetect import detect_langs
        
        # Get all detected languages with probabilities
        detections = detect_langs(text)
        
        if not detections:
            return {
                "primary_language": None,
                "primary_language_name": None,
                "confidence": 0.0,
                "detected_languages": {},
            }
        
        # Sort by probability
        sorted_detections = sorted(detections, key=lambda x: x.prob, reverse=True)
        
        # Primary language
        primary = sorted_detections[0]
        primary_lang = primary.lang if primary.lang in LANGUAGE_NAMES else None
        
        # All detected languages
        all_langs = {
            d.lang: round(d.prob, 3)
            for d in sorted_detections
            if d.lang in LANGUAGE_NAMES
        }
        
        return {
            "primary_language": primary_lang,
            "primary_language_name": LANGUAGE_NAMES.get(primary_lang, "Unknown"),
            "confidence": round(primary.prob, 3),
            "detected_languages": all_langs,
        }
    
    except Exception as e:
        print(f"⚠️  Language detection failed: {e}")
        return {
            "primary_language": None,
            "primary_language_name": None,
            "confidence": 0.0,
            "detected_languages": {},
        }


def get_language_description(language_code: str) -> str:
    """Get description of detected language for LLM context."""
    
    lang_name = LANGUAGE_NAMES.get(language_code, "Unknown")
    
    if language_code == "en":
        return f"The evidence is in {lang_name}. No translation needed."
    else:
        return (
            f"The evidence is in {lang_name} (code: {language_code}). "
            f"Use the translation tool if you need to understand specific sections. "
            f"The tool will preserve legal references (IPC sections, case numbers, etc.)."
        )


if __name__ == "__main__":
    # Test
    test_cases = [
        ("IPC धारा 354C के तहत शिकायत दर्ज की गई है।", "Hindi"),
        ("This is a sample FIR in English.", "English"),
        ("வழக்கு எண்: 123/2024", "Tamil"),
    ]
    
    print("Language Detection Tests:\n")
    for text, expected in test_cases:
        result = detect_language_with_confidence(text)
        detected = result["primary_language_name"]
        confidence = result["confidence"]
        print(f"Text: {text[:50]}...")
        print(f"Expected: {expected}, Detected: {detected} ({confidence:.2%})\n")
