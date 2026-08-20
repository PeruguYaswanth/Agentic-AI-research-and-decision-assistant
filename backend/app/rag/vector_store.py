import os
import logging
from typing import List, Optional
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from app.config import settings

logger = logging.getLogger(__name__)

# Global singleton embedding model loaded once
_embedding_model: Optional[SentenceTransformer] = None

def get_sentence_transformer_model() -> SentenceTransformer:
    """Loads and caches the SentenceTransformer model once at application startup / runtime."""
    global _embedding_model
    if _embedding_model is None:
        model_name = getattr(settings, "EMBEDDING_MODEL", "all-MiniLM-L6-v2") or "all-MiniLM-L6-v2"
        # If legacy OpenAI embedding model name is specified in env, safely fallback to all-MiniLM-L6-v2
        if "text-embedding" in model_name or "openai" in model_name.lower():
            model_name = "all-MiniLM-L6-v2"
        logger.info(f"Loading SentenceTransformer embedding model: '{model_name}'...")
        _embedding_model = SentenceTransformer(model_name)
        logger.info("SentenceTransformer embedding model loaded successfully.")
    return _embedding_model

class LocalSentenceTransformerEmbeddings(Embeddings):
    """Local sentence-transformers embedding wrapper implementing LangChain Embeddings interface."""
    def __init__(self, model: Optional[SentenceTransformer] = None):
        self.model = model or get_sentence_transformer_model()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            embeddings = self.model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"SentenceTransformer embed_documents error: {e}")
            raise e

    def embed_query(self, text: str) -> List[float]:
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"SentenceTransformer embed_query error: {e}")
            raise e

_embeddings_wrapper: Optional[LocalSentenceTransformerEmbeddings] = None

def get_embeddings_model() -> Embeddings:
    global _embeddings_wrapper
    if _embeddings_wrapper is None:
        _embeddings_wrapper = LocalSentenceTransformerEmbeddings()
    return _embeddings_wrapper

def get_vector_store() -> Chroma:
    embeddings = get_embeddings_model()
    persist_dir = settings.CHROMA_PERSIST_DIRECTORY
    os.makedirs(persist_dir, exist_ok=True)
    collection_name = "research_documents"

    # Check for dimension mismatch (e.g. legacy 1536-dim OpenAI collection vs new 384-dim local collection)
    try:
        client = chromadb.PersistentClient(path=persist_dir)
        existing_collections = [c.name for c in client.list_collections()]
        if collection_name in existing_collections:
            coll = client.get_collection(collection_name)
            peek_data = coll.peek(limit=1)
            if peek_data and peek_data.get("embeddings") is not None and len(peek_data["embeddings"]) > 0:
                existing_dim = len(peek_data["embeddings"][0])
                expected_dim = 384
                if existing_dim != expected_dim:
                    logger.warning(
                        f"Chroma collection '{collection_name}' has dimension {existing_dim}, "
                        f"expected {expected_dim}. Recreating collection to prevent conflict."
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

