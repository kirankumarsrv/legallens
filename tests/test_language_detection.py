import logging
from pathlib import Path
from collections import defaultdict

import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _has_langdetect():
    try:
        import langdetect  # noqa: F401
        return True
    except Exception:
        return False


def _detect_languages_in_text(text: str) -> dict:
    """Detect languages in text using langdetect library.
    
    Returns a dict with language codes as keys and confidence scores as values.
    """
    if not _has_langdetect():
        return {}
    
    try:
        from langdetect import detect_langs
        
        if not text or len(text.strip()) < 10:
            return {}
        
        # Split text into sentences/paragraphs to detect multiple languages
        detected_langs = {}
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            para = para.strip()
            if len(para) < 10:
                continue
            
            try:
                results = detect_langs(para)
                for result in results:
                    lang_code = result.lang
                    confidence = result.prob
                    
                    if lang_code not in detected_langs:
                        detected_langs[lang_code] = []
                    detected_langs[lang_code].append(confidence)
            except Exception as e:
                logger.debug(f"Could not detect language in paragraph: {e}")
                continue
        
        # Average the confidence scores for each language
        averaged_langs = {}
        for lang_code, scores in detected_langs.items():
            averaged_langs[lang_code] = sum(scores) / len(scores)
        
        return averaged_langs
    except Exception as e:
        logger.error(f"Error detecting languages: {e}")
        return {}


def _get_language_name(lang_code: str) -> str:
    """Convert language code to language name."""
    language_names = {
        'en': 'English',
        'hi': 'Hindi',
        'es': 'Spanish',
        'fr': 'French',
        'ta': 'Tamil',
        'de': 'German',
        'pt': 'Portuguese',
        'bn': 'Bengali',
        'mr': 'Marathi',
        'gu': 'Gujarati',
        'te': 'Telugu',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'or': 'Oriya',
        'pa': 'Punjabi',
        'ur': 'Urdu',
    }
    return language_names.get(lang_code, lang_code.upper())


@pytest.mark.smoke
def test_language_detection_in_multilingual_file():
    """Test language detection in multilingual evidence file."""
    if not _has_langdetect():
        pytest.skip("langdetect package not installed; skipping language detection test")
    
    sample = Path("evidence_samples/multilingual_sample.txt")
    assert sample.exists(), f"multilingual_sample.txt must exist under evidence_samples"
    
    logger.info("=" * 80)
    logger.info("LANGUAGE DETECTION TEST STARTED")
    logger.info("=" * 80)
    logger.info(f"Test file: {sample.absolute()}")
    
    # Read the file
    with open(sample, 'r', encoding='utf-8') as f:
        text = f.read()
    
    logger.info(f"File size: {len(text)} characters")
    logger.info(f"File content preview:\n{text[:200]}...\n")
    
    # Detect languages
    detected_langs = _detect_languages_in_text(text)
    
    logger.info("-" * 80)
    logger.info("DETECTED LANGUAGES:")
    logger.info("-" * 80)
    
    if not detected_langs:
        logger.warning("No languages detected in the file!")
        assert False, "Expected to detect at least one language"
    
    # Sort by confidence score (descending)
    sorted_langs = sorted(detected_langs.items(), key=lambda x: x[1], reverse=True)
    
    for lang_code, confidence in sorted_langs:
        lang_name = _get_language_name(lang_code)
        logger.info(f"  • {lang_name} ({lang_code}): {confidence:.2%} confidence")
    
    logger.info("-" * 80)
    logger.info(f"Total languages detected: {len(detected_langs)}")
    logger.info("=" * 80)
    
    # Assertions
    assert len(detected_langs) > 0, "Should detect at least one language"
    logger.info("✓ Test PASSED - Language detection successful!")
    logger.info("=" * 80)


@pytest.mark.smoke
def test_language_detection_in_english_file():
    """Test language detection in English-only evidence file."""
    if not _has_langdetect():
        pytest.skip("langdetect package not installed; skipping language detection test")
    
    sample = Path("evidence_samples/sample_fir.txt")
    assert sample.exists(), f"sample_fir.txt must exist under evidence_samples"
    
    logger.info("=" * 80)
    logger.info("ENGLISH FILE LANGUAGE DETECTION TEST STARTED")
    logger.info("=" * 80)
    logger.info(f"Test file: {sample.absolute()}")
    
    # Read the file
    with open(sample, 'r', encoding='utf-8') as f:
        text = f.read()
    
    logger.info(f"File size: {len(text)} characters")
    
    # Detect languages
    detected_langs = _detect_languages_in_text(text)
    
    logger.info("-" * 80)
    logger.info("DETECTED LANGUAGES:")
    logger.info("-" * 80)
    
    if not detected_langs:
        logger.warning("No languages detected in the file!")
        assert False, "Expected to detect English"
    
    # Sort by confidence score (descending)
    sorted_langs = sorted(detected_langs.items(), key=lambda x: x[1], reverse=True)
    
    for lang_code, confidence in sorted_langs:
        lang_name = _get_language_name(lang_code)
        logger.info(f"  • {lang_name} ({lang_code}): {confidence:.2%} confidence")
    
    logger.info("-" * 80)
    logger.info(f"Total languages detected: {len(detected_langs)}")
    logger.info("=" * 80)
    
    # Assertions
    assert 'en' in detected_langs, "Should detect English language"
    logger.info("✓ Test PASSED - English language detected!")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
