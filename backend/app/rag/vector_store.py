import os
import logging
from functools import lru_cache
from typing import List, Optional, Any
from langchain_core.embeddings import Embeddings

from app.config import settings

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_sentence_transformer_model():
    """
    Returns the cached singleton SentenceTransformer instance.
    Lazy loaded on first actual embedding call to ensure low memory footprint on Render.
    PyTorch thread pools are constrained to 1 thread for 512 MiB RAM compliance.
    """
    model_name = settings.EMBEDDING_MODEL or "all-MiniLM-L6-v2"
    if "embed-english" in model_name.lower() or "text-embedding" in model_name.lower():
        model_name = "all-MiniLM-L6-v2"

    logger.info(f"Loading embedding model '{model_name}' on CPU...")
    
    # Configure PyTorch CPU settings before loading model
    try:
        import torch
        torch.set_num_threads(1)
        if hasattr(torch, "set_num_interop_threads"):
            try:
                torch.set_num_interop_threads(1)
            except RuntimeError:
                pass
    except ImportError:
        pass

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name, device="cpu")
    logger.info(f"Embedding model '{model_name}' loaded successfully.")
    return model

class LocalMiniLMEmbeddings(Embeddings):
    """
    LangChain Embeddings implementation using local SentenceTransformer ('all-MiniLM-L6-v2').
    Runs locally on CPU with zero external API calls and zero billing dependencies.
    Generates normalized 384-dimensional dense vectors.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = get_sentence_transformer_model()
        try:
            try:
                import torch
                with torch.inference_mode():
                    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            except ImportError:
                embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            return [list(map(float, vec)) for vec in embeddings]
        except Exception as e:
            logger.error(f"SentenceTransformer embed_documents error: {e}")
            raise e

    def embed_query(self, text: str) -> List[float]:
        model = get_sentence_transformer_model()
        try:
            try:
                import torch
                with torch.inference_mode():
                    vec = model.encode(text, show_progress_bar=False, normalize_embeddings=True)
            except ImportError:
                vec = model.encode(text, show_progress_bar=False, normalize_embeddings=True)
            return [float(x) for x in vec]
        except Exception as e:
            logger.error(f"SentenceTransformer embed_query error: {e}")
            raise e

@lru_cache(maxsize=1)
def get_embeddings_model() -> Embeddings:
    return LocalMiniLMEmbeddings()

@lru_cache(maxsize=1)
def get_vector_store():
    """
    Initializes and returns the singleton persistent ChromaDB collection for Knowledge Base RAG.
    Ensures vector dimensionality matches 384 dimensions for all-MiniLM-L6-v2.
    """
    logger.info("Initializing vector store...")
    import chromadb
    from langchain_community.vectorstores import Chroma

    embeddings = get_embeddings_model()
    persist_dir = settings.CHROMA_PERSIST_DIRECTORY
    os.makedirs(persist_dir, exist_ok=True)
    collection_name = "research_documents"
    expected_dim = 384

    # Check for dimension mismatch (e.g. legacy 1024-dim or 1536-dim vectors)
    try:
        client = chromadb.PersistentClient(path=persist_dir)
        existing_collections = [c.name for c in client.list_collections()]
        if collection_name in existing_collections:
            coll = client.get_collection(collection_name)
            peek_data = coll.peek(limit=1)
            if peek_data and peek_data.get("embeddings") is not None and len(peek_data["embeddings"]) > 0:
                existing_dim = len(peek_data["embeddings"][0])
                if existing_dim != expected_dim:
                    logger.warning(
                        f"Chroma collection '{collection_name}' has dimension {existing_dim}, "
                        f"expected {expected_dim} for SentenceTransformer '{settings.EMBEDDING_MODEL}'. "
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
    logger.info("Vector store initialized.")
    return vector_store
