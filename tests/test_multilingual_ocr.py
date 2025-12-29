import os
from pathlib import Path

import pytest


def _has_ocr_env():
    return bool(os.environ.get("TESSERACT_CMD")) and bool(os.environ.get("POPPLER_PATH"))


def _has_python_ocr_packages():
    try:
        import pytesseract  # noqa: F401
        import pdf2image  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        return False


@pytest.mark.smoke
def test_scanned_pdf_ocr_extracts_text():
    if not _has_ocr_env():
        pytest.skip("TESSERACT_CMD or POPPLER_PATH not set; skipping OCR test")
    if not _has_python_ocr_packages():
        pytest.skip("Python OCR packages not installed; skipping OCR test")

    from workflows.lawyer_agent.evidence.parser import parse_evidence

    sample = Path("evidence_samples/scanned_sample.pdf")
    assert sample.exists(), "scanned_sample.pdf must exist under evidence_samples for this test"

    text = parse_evidence([sample])

    # Basic assertions: OCR should extract some text and include a known token from the synthetic PDF
    assert text and len(text.strip()) > 50
    assert "STATE OF EXAMPLELAND" in text or "FIR NO" in text or "Complainant" in text
