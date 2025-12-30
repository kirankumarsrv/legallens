# modules/text_extractor.py
from pypdf import PdfReader

class TextExtractor:
    """
    Extracts text content from various document formats.
 A. Build STEP 3 now - Interactive fact refiner UI (workflow nodes + state management)
    Currently supports:
    - PDF files via PyPDF (pypdf)

    This class is designed to be easily extended later
    for DOCX, HTML, or OCR-based image extraction.
    """

    def __init__(self):
        """Initialize the TextExtractor. Currently no configuration is required."""
        pass

    def extract_pdf(self, path: str) -> str:
        """
        Extract text from a PDF file.

        Parameters
        ----------
        path : str
            Absolute path to the PDF file.

        Returns
        -------
        str
            Extracted text from the PDF. Returns an empty string if extraction fails.

        Notes
        -----
        - Handles corrupted PDFs gracefully.
        - Ensures that `None` pages do not break aggregation.
        - Suitable for large PDF documents.
        """
        try:
            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
            return text.strip()
        except Exception:
            return ""
