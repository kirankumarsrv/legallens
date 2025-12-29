"""
Generate a multilingual PDF test document for OCR testing.

Creates a PDF with text in multiple languages for testing OCR + language detection pipeline.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_multilingual_pdf():
    """Create a multilingual PDF document for OCR testing."""
    
    output_path = Path("evidence_samples/multilingual_ocr_test.pdf")
    
    try:
        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "MULTILINGUAL OCR TEST DOCUMENT")
        
        y_position = height - 100
        
        # English Section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, "1. ENGLISH SECTION")
        y_position -= 25
        
        c.setFont("Helvetica", 11)
        english_text = """Police Station: Cyber Crime Cell, New Delhi
FIR Number: 12345/2024
This is a criminal case involving unauthorized access to personal data."""
        
        for line in english_text.split('\n'):
            c.drawString(50, y_position, line)
            y_position -= 18
        
        y_position -= 15
        
        # Hindi Section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, "2. HINDI SECTION")
        y_position -= 25
        
        c.setFont("Helvetica", 11)
        hindi_text = """पुलिस स्टेशन: साइबर अपराध प्रकोष्ठ, नई दिल्ली
एफआईआर संख्या: 12345/2024
यह व्यक्तिगत डेटा तक अनधिकृत पहुंच से संबंधित एक आपराधिक मामला है।"""
        
        for line in hindi_text.split('\n'):
            try:
                c.drawString(50, y_position, line)
            except:
                # If Hindi font not available, show placeholder
                c.drawString(50, y_position, "[Hindi text - font not available]")
            y_position -= 18
        
        y_position -= 15
        
        # Spanish Section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, "3. SPANISH SECTION")
        y_position -= 25
        
        c.setFont("Helvetica", 11)
        spanish_text = """Estación de Policía: Célula de Cibercrimen, Nueva Delhi
Número de FIR: 12345/2024
Este es un caso criminal que implica acceso no autorizado a datos personales."""
        
        for line in spanish_text.split('\n'):
            c.drawString(50, y_position, line)
            y_position -= 18
        
        y_position -= 15
        
        # French Section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, "4. FRENCH SECTION")
        y_position -= 25
        
        c.setFont("Helvetica", 11)
        french_text = """Poste de police: Cellule de Cybercriminalité, New Delhi
Numéro FIR: 12345/2024
Il s'agit d'une affaire criminelle impliquant un accès non autorisé à des données personnelles."""
        
        for line in french_text.split('\n'):
            c.drawString(50, y_position, line)
            y_position -= 18
        
        y_position -= 15
        
        # German Section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, "5. GERMAN SECTION")
        y_position -= 25
        
        c.setFont("Helvetica", 11)
        german_text = """Polizeistation: Abteilung für Cyberkriminalität, Neu-Delhi
FIR-Nummer: 12345/2024
Dies ist ein Straffall, der sich auf unbefugten Zugriff auf persönliche Daten bezieht."""
        
        for line in german_text.split('\n'):
            c.drawString(50, y_position, line)
            y_position -= 18
        
        # Save the PDF
        c.save()
        print(f"✅ Multilingual PDF created successfully: {output_path.absolute()}")
        return str(output_path)
        
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        return None


if __name__ == "__main__":
    create_multilingual_pdf()
