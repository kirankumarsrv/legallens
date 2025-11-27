# modules/metadata_store.py
from chromadb import PersistentClient
import os
from typing import List, Dict
import chromadb
from chromadb.config import Settings


class ChromaVectorStore: # mainly used for metadata storage
    """
    A simple metadata database using ChromaDB.

    Purpose
    -------
    - Store metadata for each legal judgment (PDF)
    - Enable fast filtering / routing based on:
        * year
        * bench size
        * case type
        * court name
        * pdf path
        * anything else you store

    This acts as your "document router" that decides:
    → Which FAISS index should be searched
    → Which document clusters belong to which year

    Attributes
    ----------
    client : chromadb.Client
        ChromaDB client instance.
    collection : chromadb.Collection
        Metadata collection used for storage/querying.
    """

    def __init__(self, persist_dir: str = "metadata_db"):
        """
        Parameters
        ----------
        persist_dir : str
            Directory where ChromaDB will persist metadata.
        """

        os.makedirs(persist_dir, exist_ok=True)

        self.client = PersistentClient(path=persist_dir)



        # Create or load collection
        self.collection = self.client.get_or_create_collection(
            name="sc_metadata",
            metadata={"hnsw:space": "cosine"}   # Not required but fine
        )

    # ----------------------------------------------------------------------
    def add_item(self, meta: Dict):
        """
        Add a single metadata dictionary to the store.

        Parameters
        ----------
        meta : dict
            Metadata dictionary from MetadataBuilder.
            Example:
            {
                "case_id": "2021_SC_0145",
                "case_name": "XYZ vs State",
                "year": 2021,
                "bench": "3-judge bench",
                "pdf_path": "...",
                "summary": "...",
                ...
            }

        Returns
        -------
        None
        """

        # Build a unique ID for the metadata
        case_id = meta.get("case_id")
        if not case_id:
            raise ValueError("Metadata must contain a 'case_id' field")

        # Chroma requires everything to be string
        metadata_str = {k: str(v) for k, v in meta.items()}



        self.collection.add(
            ids=[case_id],
            documents=[meta.get("summary", "")],  # stored, but unused
            metadatas=[metadata_str]
        )

    # ----------------------------------------------------------------------
    def add_batch(self, metas: List[Dict]):
        """
        Add multiple metadata dictionaries at once.

        Parameters
        ----------
        metas : List[dict]
            List of metadata objects.

        Returns
        -------
        None
        """

        ids = []
        docs = []
        metas_clean = []

        for meta in metas:
            cid = meta.get("case_id")
            if not cid:
                continue

            ids.append(cid)
            docs.append(meta.get("summary", ""))
            metas_clean.append({k: str(v) for k, v in meta.items()})

        self.collection.add(
            ids=ids,
            documents=docs,
            metadatas=metas_clean
        )

    # ----------------------------------------------------------------------
    def query(self, filters: Dict, limit: int = 50) -> List[Dict]:
        """
        Query metadata using filters.

        Parameters
        ----------
        filters : dict
            Example:
            {"year": "2017"}
            {"bench": "5-judge"}
            {"case_type": "criminal"}

        limit : int
            Max number of results to return.

        Returns
        -------
        List[dict]
            List of metadata dicts matching filter.
        """

        results = self.collection.get(
            where=filters,
            limit=limit
        )

        # Convert results back to python dicts
        metadatas = results.get("metadatas", [])
        return metadatas

    # ----------------------------------------------------------------------
    def get_by_year(self, year: int) -> List[Dict]:
        """
        Convenience function for querying by year.

        Parameters
        ----------
        year : int
            Judgment year.

        Returns
        -------
        List[dict]
            All metadata entries with this year.
        """
        return self.query({"year": str(year)})

    # ----------------------------------------------------------------------
    def delete(self, case_id: str):
        """
        Delete a metadata entry.

        Parameters
        ----------
        case_id : str
            Unique ID of the case.

        Returns
        -------
        None
        """
        self.collection.delete(ids=[case_id])




    def add_embeddings(self, ids, embeddings, metadatas, documents, batch_size=5000):
        """
        Add embeddings to Chroma in safe batches (max ≈5461).
        """

        n = len(ids)
        if not (n == len(embeddings) == len(metadatas) == len(documents)):
            raise ValueError("All arrays must have same length")

        metas_clean = [{k: str(v) for k, v in meta.items()} for meta in metadatas]

        for i in range(0, n, batch_size):
            print(f"Adding batch {i//batch_size + 1}...")
            self.collection.add(
                ids=ids[i:i+batch_size],
                embeddings=embeddings[i:i+batch_size],
                metadatas=metas_clean[i:i+batch_size],
                documents=documents[i:i+batch_size],
            )
