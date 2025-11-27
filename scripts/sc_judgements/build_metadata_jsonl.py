import os
import sys
import json
from dotenv import load_dotenv

# ---------------------------------------------------------
# Allow imports from modules/
# ---------------------------------------------------------
ROOT_DIR = os.getcwd()
sys.path.append(ROOT_DIR)

print("ROOT_DIR set to:", ROOT_DIR)
# Load .env variables
load_dotenv()

# ---------------------------------------------------------
from modules.loader import Loader
from modules.text_extractor import TextExtractor
from modules.llm_manager import LLMManager
from scripts.sc_judgements.metadata_builder import MetadataBuilder


OUTPUT_PATH = "datasets/sc_data/metadata/sc_metadata.jsonl"


def main():

    # STEP 1: Load PDFs
    loader = Loader(r"C:\Users\kiran\Desktop\law ai\datasets\sc_data")
    pdf_paths = loader.load_sc_judgment_pdfs()
    print(f"Found {len(pdf_paths)} PDF files")

    if not pdf_paths:
        print("No PDFs found, exiting.")
        return

    # STEP 2: Initialize Text Extractor
    extractor = TextExtractor()

    # STEP 3: Initialize Groq LLM Manager
    llm = LLMManager(
        provider="groq",
        model_name="llama-3.3-70b-versatile"   # best for legal summarization
    )

    # STEP 4: Metadata Builder
    builder = MetadataBuilder(llm)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # STEP 5: Open JSONL file in append mode
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:

        for idx, pdf_path in enumerate(pdf_paths, start=1):
            print(f"\n[{idx}/{len(pdf_paths)}] Processing:", pdf_path)

            # Extract text
            text = extractor.extract_pdf(pdf_path)
            if not text:
                print("⚠️  Empty text in PDF, skipping.")
                continue

            # Build metadata using LLM
            meta = builder.build_metadata(pdf_path, text)

            # Write to JSONL
            f.write(json.dumps(meta) + "\n")

            print("✓ Saved metadata for:", os.path.basename(pdf_path))

    print("\n🎉 All metadata saved successfully!")
    print("Output file:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
