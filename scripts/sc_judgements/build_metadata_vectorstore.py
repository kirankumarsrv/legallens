import os
import sys
import json
from dotenv import load_dotenv

from langchain_core.documents import Document

# ---------------------------------------------------------
# Fix import paths
# ---------------------------------------------------------
ROOT_DIR = os.getcwd()
sys.path.append(ROOT_DIR)
print("ROOT_DIR set to:", ROOT_DIR)

from modules.embedding_manager import EmbeddingManager
from modules.vector_store.chroma_vector_store import ChromaVectorStore


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
METADATA_FILE = "datasets/sc_data/metadata/sc_metadata.jsonl"
VECTOR_DB_DIR = "vector_db/metadata"


def load_metadata(jsonl_path: str):
    """Load metadata.jsonl → list of dicts
    Input: path to JSONL
    Output: list of metadata dicts
    """
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def build_documents(metadata_list):
    """Convert metadata rows → LangChain Document objects"""
    docs = []

    for meta in metadata_list:
        case_name = meta.get("case_name", "")
        year = meta.get("year", "")
        citations = meta.get("citations", [])
        summary = meta.get("summary", "")
        pdf_path = meta.get("pdf_path", "")

        content = f"""
CASE NAME: {case_name}
YEAR: {year}
CITATIONS: {citations}
SUMMARY: {summary}
PDF: {pdf_path}
"""

        doc = Document(
            page_content=content.strip(),
            metadata={
                "year": year,
                "pdf_path": pdf_path,
                "case_name": case_name,
                # "cittaions": citations,
                # "summary": summary,

            }
        )

        docs.append(doc)

    return docs


def main():
    print("\n=== LOADING ENVIRONMENT ===")
    load_dotenv()

    print("\n=== STEP 1: Load metadata.jsonl ===")
    metadata_list = load_metadata(METADATA_FILE)
    print(f"Loaded {len(metadata_list)} metadata records.")

    print("\n=== STEP 2: Convert to Document objects ===")
    docs = build_documents(metadata_list)
    print(f"Prepared {len(docs)} documents.")

    print("\n=== STEP 3: Initialize Embedding Model ===")
    embedder = EmbeddingManager(model_name="BAAI/bge-base-en-v1.5",device="cuda")

    print("\n=== STEP 4: Generate embeddings (this may take time) ===")
    texts = [d.page_content for d in docs]
    embeddings = embedder.embed_documents(texts)


    print("\n=== STEP 5: Initialize Chroma Vector Store ===")
    vs = ChromaVectorStore(persist_dir=VECTOR_DB_DIR)

    print("\n=== STEP 6: Add embeddings to Chroma ===")
    ids = [f"meta_{i}" for i in range(len(docs))]
    metadatas = [d.metadata for d in docs]

    
    
    vs.add_embeddings(ids=ids, embeddings=embeddings, metadatas=metadatas,  documents=texts)

    print("\n=== STEP 7: Persist DB ===")


    print("\n🎉 DONE! Metadata Vector Store Built Successfully!")
    print(f"📁 Location: {VECTOR_DB_DIR}")


if __name__ == "__main__":
    main()
