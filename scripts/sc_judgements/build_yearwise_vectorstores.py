import os
import sys
from dotenv import load_dotenv

from langchain_core.documents import Document

ROOT_DIR = os.getcwd()
sys.path.append(ROOT_DIR)

print("ROOT_DIR set to:", ROOT_DIR)

from modules.loader import Loader
from modules.text_extractor import TextExtractor
from modules.text_splitter import LegalParagraphSplitter
from modules.embedding_manager import EmbeddingManager
from modules.vector_store.FAISS_vector_store import FAISSVectorStore


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
DATASET_DIR = r"C:\Users\kiran\Desktop\law ai\datasets\sc_data"
VECTOR_DB_DIR = "vector_db/yearwise"


def extract_year_from_path(pdf_path: str):
    parts = pdf_path.replace("\\", "/").split("/")
    for p in parts:
        if p.isdigit():
            return int(p)
    return None


def main():
    print("\n=== LOADING ENV ===")
    load_dotenv()

    print("\n=== STEP 1: Load all PDFs ===")
    loader = Loader(DATASET_DIR)
    pdf_paths = loader.load_sc_judgment_pdfs()
    print(f"Found {len(pdf_paths)} PDFs.")

    # Organize by year
    year_map = {}
    for path in pdf_paths:
        year = extract_year_from_path(path)
        if not year:
            continue
        year_map.setdefault(year, []).append(path)

    print("\nYEARS FOUND:", list(year_map.keys()))

    extractor = TextExtractor()
    splitter = LegalParagraphSplitter()
    embedder = EmbeddingManager(model_name="BAAI/bge-base-en-v1.5",device="cuda")

    # Create vector_db/yearwise folder
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)

    # --------------------------------------------------
    # Process each year independently
    # --------------------------------------------------
    for year, paths in year_map.items():
        if (year<1967):
            break
        print("\n===============================")
        print(f"Building vector DB for YEAR={year}")
        # print(f"PDF count: {paths}")
        print(f"PDF count: {len(paths)}")
        print("===============================")

        year_dir = os.path.join(VECTOR_DB_DIR, str(year))
        os.makedirs(year_dir, exist_ok=True)

        vs = FAISSVectorStore(embedding_model=embedder)

        for pdf_path in paths:
            print(f"\n→ Processing: {pdf_path}")

            # Extract text
            text = extractor.extract_pdf(pdf_path)
            if not text:
                print("⚠️ Empty text — skipping.")
                continue

            # Split to paragraphs/chunks
            chunks = splitter.split(text)
            print(f"  Chunks created: {len(chunks)}")

            # Convert to Documents
            docs = [
                Document(
                    page_content=chunk,
                    metadata={"pdf_path": pdf_path, "year": year}
                )
                for chunk in chunks
            ]

            # Add to vector DB
            vs.build_from_chunks(docs)

        # Save FAISS DB
        print(f"\nSaving FAISS DB for {year}...")
        vs.save(year_dir)

    print("\n🎉 DONE! YEAR-WISE Vector DBs created successfully.")
    print(f"Output folder: {VECTOR_DB_DIR}")


if __name__ == "__main__":
    main()
