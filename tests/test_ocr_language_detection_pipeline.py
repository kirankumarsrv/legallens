"""
OCR + Language Detection Pipeline Test

Comprehensive test that:
1. Extracts text from multilingual scanned PDFs using OCR (Tesseract)
2. Detects languages in the extracted text (langdetect)
3. Logs detailed results with confidence scores

This test requires:
- Tesseract-OCR installed and TESSERACT_CMD environment variable set
- Poppler installed and POPPLER_PATH environment variable set
- Python packages: pdf2image, pytesseract, langdetect
"""

import logging
import os
from pathlib import Path
from collections import defaultdict

import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _has_ocr_env():
    """Check if OCR environment is properly configured."""
    has_tesseract = bool(os.environ.get("TESSERACT_CMD"))
    has_poppler = bool(os.environ.get("POPPLER_PATH"))
    return has_tesseract and has_poppler


def _has_ocr_packages():
    """Check if OCR Python packages are installed."""
    try:
        import pytesseract  # noqa: F401
        import pdf2image  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        return False


def _has_langdetect():
    """Check if langdetect package is installed."""
    try:
        import langdetect  # noqa: F401
        return True
    except Exception:
        return False


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using OCR."""
    if not _has_ocr_packages():
        return ""
    
    try:
        from pdf2image import convert_from_path
        import pytesseract
        
        # Set tesseract path from environment
        tesseract_cmd = os.environ.get("TESSERACT_CMD")
        if tesseract_cmd:
            from pytesseract import pytesseract as pyt
            pyt.tesseract_cmd = tesseract_cmd
            logger.info(f"Using Tesseract from: {tesseract_cmd}")
        
        logger.info(f"Converting PDF to images: {pdf_path.name}")
        
        # Get poppler path from environment
        poppler_path = os.environ.get("POPPLER_PATH")
        
        if poppler_path:
            logger.info(f"Using Poppler from: {poppler_path}")
            images = convert_from_path(str(pdf_path), poppler_path=poppler_path)
        else:
            images = convert_from_path(str(pdf_path))
        
        logger.info(f"  → Generated {len(images)} image(s)")
        
        all_text = []
        for idx, image in enumerate(images):
            logger.info(f"  → Running OCR on page {idx + 1}...")
            text = pytesseract.image_to_string(image)
            all_text.append(text)
        
        combined_text = "\n".join(all_text)
        return combined_text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""


def _detect_languages_in_text(text: str) -> dict:
    """Detect languages in text using langdetect.
    
    Returns a dict with language codes as keys and confidence scores as values.
    """
    if not _has_langdetect():
        return {}
    
    try:
        from langdetect import detect_langs
        
        if not text or len(text.strip()) < 10:
            return {}
        
        # Split text into paragraphs to detect multiple languages
        detected_langs = {}
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        logger.info(f"Analyzing {len(paragraphs)} paragraphs for language detection...")
        
        for idx, para in enumerate(paragraphs):
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
                logger.debug(f"Could not detect language in paragraph {idx}: {e}")
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
        'id': 'Indonesian',
        'ja': 'Japanese',
        'zh-cn': 'Chinese (Simplified)',
        'zh-tw': 'Chinese (Traditional)',
        'ar': 'Arabic',
        'ru': 'Russian',
    }
    return language_names.get(lang_code, lang_code.upper())


@pytest.mark.smoke
def test_ocr_plus_language_detection_multilingual_pdf():
    """Complete pipeline test: OCR + Language Detection on multilingual PDF."""
    
    if not _has_ocr_env():
        pytest.skip("TESSERACT_CMD or POPPLER_PATH not set; skipping OCR test")
    if not _has_ocr_packages():
        pytest.skip("Python OCR packages not installed; skipping OCR test")
    if not _has_langdetect():
        pytest.skip("langdetect package not installed; skipping language detection")
    
    pdf_path = Path("evidence_samples/multilingual_ocr_test.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"{pdf_path.name} not found; create it first using scripts/generate_multilingual_pdf.py")
    
    logger.info("=" * 100)
    logger.info("OCR + LANGUAGE DETECTION PIPELINE TEST - MULTILINGUAL PDF")
    logger.info("=" * 100)
    logger.info(f"Test file: {pdf_path.absolute()}")
    logger.info(f"File size: {pdf_path.stat().st_size} bytes")
    
    # Step 1: Extract text using OCR
    logger.info("\n" + "-" * 100)
    logger.info("STEP 1: OCR TEXT EXTRACTION")
    logger.info("-" * 100)
    
    extracted_text = _extract_text_from_pdf(pdf_path)
    
    assert extracted_text and len(extracted_text.strip()) > 50, \
        "OCR should extract meaningful text from PDF"
    
    logger.info(f"✓ Successfully extracted {len(extracted_text)} characters from PDF")
    logger.info(f"Text preview:\n{extracted_text[:300]}...\n")
    
    # Step 2: Detect languages
    logger.info("-" * 100)
    logger.info("STEP 2: LANGUAGE DETECTION")
    logger.info("-" * 100)
    
    detected_langs = _detect_languages_in_text(extracted_text)
    
    assert len(detected_langs) > 0, "Should detect at least one language in extracted text"
    
    # Sort by confidence score (descending)
    sorted_langs = sorted(detected_langs.items(), key=lambda x: x[1], reverse=True)
    
    logger.info(f"Detected {len(sorted_langs)} language(s):\n")
    for rank, (lang_code, confidence) in enumerate(sorted_langs, 1):
        lang_name = _get_language_name(lang_code)
        logger.info(f"  {rank}. {lang_name:20} ({lang_code}): {confidence:6.2%} confidence")
    
    # Step 3: Summary
    logger.info("\n" + "-" * 100)
    logger.info("STEP 3: PIPELINE SUMMARY")
    logger.info("-" * 100)
    logger.info(f"✓ OCR Status: SUCCESS - Extracted {len(extracted_text)} characters")
    logger.info(f"✓ Language Detection Status: SUCCESS - Detected {len(detected_langs)} language(s)")
    logger.info(f"✓ Primary Language: {_get_language_name(sorted_langs[0][0])} ({sorted_langs[0][1]:.2%})")
    logger.info("=" * 100)


@pytest.mark.smoke
def test_ocr_plus_language_detection_english_pdf():
    """Complete pipeline test: OCR + Language Detection on English scanned PDF."""
    
    if not _has_ocr_env():
        pytest.skip("TESSERACT_CMD or POPPLER_PATH not set; skipping OCR test")
    if not _has_ocr_packages():
        pytest.skip("Python OCR packages not installed; skipping OCR test")
    if not _has_langdetect():
        pytest.skip("langdetect package not installed; skipping language detection")
    
    pdf_path = Path("evidence_samples/scanned_sample.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"{pdf_path.name} not found")
    
    logger.info("=" * 100)
    logger.info("OCR + LANGUAGE DETECTION PIPELINE TEST - ENGLISH SCANNED PDF")
    logger.info("=" * 100)
    logger.info(f"Test file: {pdf_path.absolute()}")
    logger.info(f"File size: {pdf_path.stat().st_size} bytes")
    
    # Step 1: Extract text using OCR
    logger.info("\n" + "-" * 100)
    logger.info("STEP 1: OCR TEXT EXTRACTION")
    logger.info("-" * 100)
    
    extracted_text = _extract_text_from_pdf(pdf_path)
    
    assert extracted_text and len(extracted_text.strip()) > 50, \
        "OCR should extract meaningful text from PDF"
    
    logger.info(f"✓ Successfully extracted {len(extracted_text)} characters from PDF")
    logger.info(f"Text preview:\n{extracted_text[:300]}...\n")
    
    # Step 2: Detect languages
    logger.info("-" * 100)
    logger.info("STEP 2: LANGUAGE DETECTION")
    logger.info("-" * 100)
    
    detected_langs = _detect_languages_in_text(extracted_text)
    
    assert len(detected_langs) > 0, "Should detect at least one language in extracted text"
    
    # Verify English is detected
    assert 'en' in detected_langs, "English should be detected in English PDF"
    
    # Sort by confidence score (descending)
    sorted_langs = sorted(detected_langs.items(), key=lambda x: x[1], reverse=True)
    
    logger.info(f"Detected {len(sorted_langs)} language(s):\n")
    for rank, (lang_code, confidence) in enumerate(sorted_langs, 1):
        lang_name = _get_language_name(lang_code)
        logger.info(f"  {rank}. {lang_name:20} ({lang_code}): {confidence:6.2%} confidence")
    
    # Step 3: Summary
    logger.info("\n" + "-" * 100)
    logger.info("STEP 3: PIPELINE SUMMARY")
    logger.info("-" * 100)
    logger.info(f"✓ OCR Status: SUCCESS - Extracted {len(extracted_text)} characters")
    logger.info(f"✓ Language Detection Status: SUCCESS - Detected {len(detected_langs)} language(s)")
    logger.info(f"✓ Primary Language: {_get_language_name(sorted_langs[0][0])} ({sorted_langs[0][1]:.2%})")
    logger.info(f"✓ English Confidence: {detected_langs.get('en', 0):.2%}")
    logger.info("=" * 100)


if __name__ == "__main__":
    # Run tests with verbose output and logging
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
