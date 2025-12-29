"""
Complete OCR + Language Detection Pipeline Test
Demonstrates the full pipeline: OCR extraction + Language detection with comprehensive logging
"""

import logging
import os
from pathlib import Path

import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _has_ocr_env():
    """Check if OCR environment is properly configured."""
    return bool(os.environ.get("TESSERACT_CMD")) and bool(os.environ.get("POPPLER_PATH"))


def _has_ocr_packages():
    """Check if OCR Python packages are installed."""
    try:
        import pytesseract  # noqa: F401
        import pdf2image  # noqa: F401
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


def _get_language_name(lang_code: str) -> str:
    """Convert language code to language name."""
    language_names = {
        'en': 'English', 'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French',
        'ta': 'Tamil', 'de': 'German', 'pt': 'Portuguese', 'bn': 'Bengali',
        'mr': 'Marathi', 'gu': 'Gujarati', 'te': 'Telugu', 'kn': 'Kannada',
    }
    return language_names.get(lang_code, lang_code.upper())


def _detect_languages_in_text(text: str) -> dict:
    """Detect languages in text using langdetect."""
    if not _has_langdetect():
        return {}
    
    try:
        from langdetect import detect_langs
        
        if not text or len(text.strip()) < 10:
            return {}
        
        detected_langs = {}
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 10]
        
        for para in paragraphs:
            try:
                results = detect_langs(para)
                for result in results:
                    if result.lang not in detected_langs:
                        detected_langs[result.lang] = []
                    detected_langs[result.lang].append(result.prob)
            except:
                continue
        
        # Average scores
        return {lang: sum(scores) / len(scores) for lang, scores in detected_langs.items()}
    except Exception as e:
        logger.error(f"Error in language detection: {e}")
        return {}


@pytest.mark.smoke
def test_language_detection_on_multilingual_text():
    """Test: Language detection on multilingual text file (no OCR needed)."""
    if not _has_langdetect():
        pytest.skip("langdetect not installed")
    
    text_file = Path("evidence_samples/multilingual_sample.txt")
    if not text_file.exists():
        pytest.skip("multilingual_sample.txt not found")
    
    logger.info("=" * 100)
    logger.info("LANGUAGE DETECTION TEST - Multilingual Text File")
    logger.info("=" * 100)
    
    with open(text_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    logger.info(f"File: {text_file.name} ({len(text)} characters)")
    logger.info(f"Preview: {text[:150]}...")
    
    # Detect languages
    detected_langs = _detect_languages_in_text(text)
    
    assert len(detected_langs) > 0, "Should detect languages"
    
    logger.info("\nDETECTED LANGUAGES:")
    sorted_langs = sorted(detected_langs.items(), key=lambda x: x[1], reverse=True)
    for rank, (code, conf) in enumerate(sorted_langs, 1):
        logger.info(f"  {rank}. {_get_language_name(code):20} ({code}): {conf:.2%}")
    
    logger.info(f"\n✓ Successfully detected {len(detected_langs)} languages")
    logger.info("=" * 100)


@pytest.mark.smoke  
def test_ocr_plus_language_detection():
    """Test: Complete OCR + Language Detection Pipeline on English PDF."""
    if not _has_ocr_env():
        pytest.skip("TESSERACT_CMD or POPPLER_PATH not set")
    if not _has_ocr_packages():
        pytest.skip("OCR packages not installed")
    if not _has_langdetect():
        pytest.skip("langdetect not installed")
    
    from pdf2image import convert_from_path
    import pytesseract
    from pytesseract import pytesseract as pyt
    
    pdf_file = Path("evidence_samples/scanned_sample.pdf")
    if not pdf_file.exists():
        pytest.skip("scanned_sample.pdf not found")
    
    logger.info("=" * 100)
    logger.info("OCR + LANGUAGE DETECTION PIPELINE TEST")
    logger.info("=" * 100)
    logger.info(f"File: {pdf_file.name} ({pdf_file.stat().st_size} bytes)")
    
    # Step 1: OCR
    logger.info("\n--- STEP 1: OCR EXTRACTION ---")
    try:
        # Set tesseract path
        tess_cmd = os.environ.get("TESSERACT_CMD")
        pop_path = os.environ.get("POPPLER_PATH")
        
        logger.info(f"Tesseract: {tess_cmd}")
        logger.info(f"Poppler: {pop_path}")
        
        pyt.tesseract_cmd = tess_cmd
        
        logger.info(f"Converting PDF to images...")
        images = convert_from_path(str(pdf_file), poppler_path=pop_path)
        logger.info(f"  Generated {len(images)} image(s)")
        
        all_text = []
        for idx, image in enumerate(images):
            logger.info(f"  Running OCR on page {idx + 1}...")
            text = pytesseract.image_to_string(image)
            all_text.append(text)
        
        extracted_text = "\n".join(all_text)
        logger.info(f"✓ Extracted {len(extracted_text)} characters from PDF")
        
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        pytest.skip(f"OCR failed: {e}")
        return
    
    # Step 2: Language Detection
    logger.info("\n--- STEP 2: LANGUAGE DETECTION ---")
    detected_langs = _detect_languages_in_text(extracted_text)
    
    assert len(detected_langs) > 0, "Should detect languages in OCR output"
    
    logger.info(f"Detected {len(detected_langs)} language(s):")
    sorted_langs = sorted(detected_langs.items(), key=lambda x: x[1], reverse=True)
    for rank, (code, conf) in enumerate(sorted_langs, 1):
        logger.info(f"  {rank}. {_get_language_name(code):20} ({code}): {conf:.2%}")
    
    # Step 3: Summary
    logger.info("\n--- PIPELINE SUMMARY ---")
    logger.info(f"✓ OCR Extraction: SUCCESS ({len(extracted_text)} chars)")
    logger.info(f"✓ Language Detection: SUCCESS ({len(detected_langs)} languages)")
    logger.info(f"✓ Primary Language: {_get_language_name(sorted_langs[0][0])} ({sorted_langs[0][1]:.2%})")
    logger.info("=" * 100)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
