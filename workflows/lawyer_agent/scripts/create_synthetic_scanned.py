"""
Create a synthetic scanned PDF for OCR testing at `evidence_samples/scanned_sample.pdf`.

Generates a simple image with legal-style text and saves as a one-page PDF.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def main():
    base = Path(__file__).resolve().parents[2]
    out_dir = base / "evidence_samples"
    out_dir.mkdir(exist_ok=True)

    out_path = out_dir / "scanned_sample.pdf"

    # Image size suitable for OCR
    img = Image.new("RGB", (1654, 2339), color="white")  # A4 at 150 DPI approx
    draw = ImageDraw.Draw(img)

    # Use default PIL font; system may not have large fonts
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()

    text = (
        "STATE OF EXAMPLELAND\n"
        "FIR NO: 9876/2024\n\n"
        "Complainant: Ramesh Kumar\n"
        "Accused: Unknown\n\n"
        "On October 15, 2024 at approximately 10:30 PM, the complainant alleges that an unauthorised\n"
        "person accessed the complainant's email account and downloaded private correspondence. The\n"
        "incident was reported to the Cyber Crime Cell, Example City on November 10, 2024.\n\n"
        "Sections invoked: 420, 406, 354C\n"
    )

    margin = 80
    y = margin
    for line in text.split("\n"):
        draw.text((margin, y), line, font=font, fill=(0, 0, 0))
        y += 40

    # Save as PDF
    img.save(out_path, "PDF", resolution=150)
    print(f"Created synthetic scanned PDF: {out_path}")


if __name__ == "__main__":
    main()
