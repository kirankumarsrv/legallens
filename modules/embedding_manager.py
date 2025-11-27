# modules/embedding_manager.py

from typing import List, Optional
from langchain_huggingface import HuggingFaceEmbeddings


class EmbeddingManager:
    """
    A modular embedding manager responsible for generating vector embeddings
    for text chunks and queries.

    This class wraps HuggingFace embedding models and provides a clean,
    consistent interface for embedding both documents and queries.

    Attributes
    ----------
    model_name : str
        Name of the HuggingFace embedding model.
    device : str or None
        Computation device ("cpu", "cuda", "mps", or None for auto).
    embedder : HuggingFaceEmbeddings
        Underlying embedding model instance.
    """


    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        device: Optional[str] = None,
    ):
        """
        Initialize the embedding manager and load the HuggingFace embedding model.

        Parameters
        ----------
        model_name : str, optional
            Name of the HF model to load. Defaults to "BAAI/bge-base-en-v1.5".
        device : str or None, optional
            Device for inference. Can be "cpu", "cuda", "mps", or None.
            If None, the backend decides automatically.

        Raises
        ------
        ValueError
            If the embedding model fails to load.
        """

        self.model_name = model_name
        self.device = device

        try:
            self.embedder = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs={"device": self.device} if self.device else {}
            )
        except Exception as e:
            raise ValueError(f"Failed to load embedding model '{model_name}': {e}")

    # ------------------------------------------------------------------
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text documents (chunks).

        Parameters
        ----------
        documents : List[str]
            A list of text strings representing chunks extracted
            from legal judgments or other documents.

        Returns
        -------
        List[List[float]]
            A list where each element is the embedding vector (list of floats)
            corresponding to one input document.

        Raises
        ------
        ValueError
            If documents is empty or not a list of strings.
        """

        if not documents or not isinstance(documents, list):
            raise ValueError("documents must be a non-empty list of strings")

        return self.embedder.embed_documents(documents)

    # ------------------------------------------------------------------
    def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a single search/query string.

        Parameters
        ----------
        query : str
            A single text query (e.g., "Article 21 fundamental rights").

        Returns
        -------
        List[float]
            A single embedding vector representing the semantic meaning of the query.

        Raises
        ------
        ValueError
            If query is not a string.
        """

        if not isinstance(query, str):
            raise ValueError("query must be a string")

        return self.embedder.embed_query(query)

    # ------------------------------------------------------------------
    def get_model_info(self) -> dict:
        """
        Retrieve information about the currently loaded embedding model.

        Returns
        -------
        dict
            Dictionary containing:
            - model_name : str
            - device : str
            - description : str
        """

        return {
            "model_name": self.model_name,
            "device": self.device or "auto",
            "description": "Vector embedding model used for semantic search."
        }

    # ⭐⭐ IMPORTANT FIX ⭐⭐
    def __call__(self, text: str):
        """FAISS requires a callable embedding_function."""
        return self.embed_query(text)