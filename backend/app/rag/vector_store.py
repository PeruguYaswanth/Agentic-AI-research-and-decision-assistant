import os
import logging
from typing import List, Optional
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
import cohere
from app.config import settings

logger = logging.getLogger(__name__)

class CohereEmbeddings(Embeddings):
    """
    Cohere API embedding client implementing LangChain Embeddings interface.
    Uses 'search_document' for document indexing and 'search_query' for query retrieval.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "embed-english-v3.0"):
        self.api_key = (api_key or getattr(settings, "COHERE_API_KEY", None) or os.getenv("COHERE_API_KEY", "") or "").strip()
        self.model = model or getattr(settings, "EMBEDDING_MODEL", "embed-english-v3.0")
        # Ensure legacy or mismatched model names default safely to embed-english-v3.0
        if "text-embedding" in self.model or "all-minilm" in self.model.lower():
            self.model = "embed-english-v3.0"
        self._client: Optional[cohere.Client] = None

    def _get_client(self) -> Optional[cohere.Client]:
        if self._client is None and self.api_key and not self.api_key.startswith("your_"):
            try:
                self._client = cohere.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Cohere client: {e}")
                self._client = None
        return self._client

    def _fallback_embed(self, text: str, dim: int = 1024) -> List[float]:
        """Lightweight, zero-memory deterministic 1024-dim vector fallback when COHERE_API_KEY is not set."""
        import hashlib
        import math
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(dim):
            byte_val = h[i % len(h)]
            val = math.sin((i + 1) * (byte_val + 1))
            vec.append(val)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        if client:
            try:
                response = client.embed(
                    texts=texts,
                    model=self.model,
                    input_type="search_document"
                )
                return [list(map(float, vec)) for vec in response.embeddings]
            except Exception as e:
                logger.error(f"Cohere embed_documents error: {e}")
                raise e
        else:
            logger.warning("No valid COHERE_API_KEY configured. Using deterministic fallback embeddings (1024-dim).")
            return [self._fallback_embed(t, dim=1024) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        client = self._get_client()
        if client:
            try:
                response = client.embed(
                    texts=[text],
                    model=self.model,
                    input_type="search_query"
                )
                return [float(x) for x in response.embeddings[0]]
            except Exception as e:
                logger.error(f"Cohere embed_query error: {e}")
                raise e
        else:
            logger.warning("No valid COHERE_API_KEY configured. Using deterministic fallback embeddings (1024-dim).")
            return self._fallback_embed(text, dim=1024)

_embeddings_instance: Optional[CohereEmbeddings] = None

def get_embeddings_model() -> Embeddings:
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = CohereEmbeddings()
    return _embeddings_instance

def get_vector_store() -> Chroma:
    embeddings = get_embeddings_model()
    persist_dir = settings.CHROMA_PERSIST_DIRECTORY
    os.makedirs(persist_dir, exist_ok=True)
    collection_name = "research_documents"

    # Check for dimension mismatch (e.g. legacy 1536 OpenAI or 384 MiniLM vs 1024 Cohere)
    try:
        client = chromadb.PersistentClient(path=persist_dir)
        existing_collections = [c.name for c in client.list_collections()]
        if collection_name in existing_collections:
            coll = client.get_collection(collection_name)
            peek_data = coll.peek(limit=1)
            if peek_data and peek_data.get("embeddings") is not None and len(peek_data["embeddings"]) > 0:
                existing_dim = len(peek_data["embeddings"][0])
                expected_dim = 1024
                if existing_dim != expected_dim:
                    logger.warning(
                        f"Chroma collection '{collection_name}' has dimension {existing_dim}, "
                        f"expected {expected_dim} for Cohere '{settings.EMBEDDING_MODEL}'. "
                        f"Recreating collection to prevent dimensionality mismatch."
                    )
                    client.delete_collection(collection_name)
    except Exception as e:
        logger.warning(f"Chroma collection dimensionality check warning: {e}")

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir
    )
    return vector_store

