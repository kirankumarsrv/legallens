# modules/vector_store_manager.py

import os
from typing import List, Dict
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS


class FAISSVectorStore: #written mainly for year wise sc judgements
    """
    A manager for creating, saving, loading, and querying FAISS vector stores.

    Handles:
    - Adding chunk embeddings
    - Metadata storage
    - Similarity search
    - Saving/loading FAISS index files

    Attributes
    ----------
    embedding_model : EmbeddingManager
        Your custom embedding manager used to embed documents.
    vectorstore : FAISS or None
        In-memory FAISS index.
    """

    def __init__(self, embedding_model):
        """
        Parameters
        ----------
        embedding_model : EmbeddingManager
            A reference to your embedding module (embedding_manager.py).
        """
        self.embedding_model = embedding_model
        self.vectorstore = None

    def build_from_chunks(self, chunks):
        """
        Build or extend a FAISS vector store from a list of Document objects.
        chunks: List[Document]
        """

        # ✔ chunks are already Document objects
        documents = chunks  

        # 🧠 First-time creation
        if self.vectorstore is None:
            self.vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embedding_model
            )
        else:
            # ➕ Append new documents
            self.vectorstore.add_documents(documents)

        return self.vectorstore


    # --------------------------------------------------------------
    # def build_from_chunks(self, chunks: List[Dict]) -> FAISS:
    #     """
    #     Build a new FAISS store from text chunks.

    #     Parameters
    #     ----------
    #     chunks : List[dict]
    #         List of chunk dictionaries with:
    #         {
    #             "chunk_id": "...",
    #             "text": "...",
    #             "start_index": int,
    #             "end_index": int
    #         }

    #     Returns
    #     -------
    #     FAISS
    #         A FAISS vector store containing all chunk embeddings.
    #     """

    #     documents = []
    #     for ch in chunks:
    #         documents.append(
    #             Document(
    #                 page_content=ch["text"],
    #                 metadata={"chunk_id": ch["chunk_id"]}
    #             )
    #         )

    #     # Joke: embedding all chunks is like eating all biriyani at once — dangerous but satisfying 😄

    #     self.vectorstore = FAISS.from_documents(
    #         documents=documents,
    #         embedding=self.embedding_model
    #     )

    #     return self.vectorstore

    # --------------------------------------------------------------
    def save(self, path: str):
        """
        Save FAISS index + metadata to a directory.

        Parameters
        ----------
        path : str
            Directory where FAISS index files will be stored.
        """
        if self.vectorstore is None:
            raise ValueError("Vector store not built yet.")

        os.makedirs(path, exist_ok=True)
        self.vectorstore.save_local(path)

    # --------------------------------------------------------------
    def load(self, path: str):
        """
        Load a previously saved FAISS index.

        Parameters
        ----------
        path : str
            Directory containing FAISS index and metadata.

        Returns
        -------
        FAISS
            Loaded vector store.
        """
        self.vectorstore = FAISS.load_local(
            path,
            embeddings=self.embedding_model,
            allow_dangerous_deserialization=True
        )
        return self.vectorstore

    # --------------------------------------------------------------
    def similarity_search(self, query: str, k: int = 5):
        """
        Perform semantic similarity search.

        Parameters
        ----------
        query : str
            Text query to search for.
        k : int, optional
            Number of results to return. Defaults to 5.

        Returns
        -------
        List[Document]
            Top matching chunks as Document objects.
        """

        if self.vectorstore is None:
            raise ValueError("Vector store not loaded or built.")

        return self.vectorstore.similarity_search(query, k=k)
