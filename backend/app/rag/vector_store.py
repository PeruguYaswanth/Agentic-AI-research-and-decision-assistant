import os
import logging
from typing import List
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from app.config import settings

logger = logging.getLogger(__name__)

class LocalChromaEmbeddings(Embeddings):
    """Local ONNX-based all-MiniLM-L6-v2 embeddings when no OpenAI API key is configured."""
    def __init__(self):
        import chromadb.utils.embedding_functions as ef
        self.fn = ef.DefaultEmbeddingFunction()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            vectors = self.fn(texts)
            return [list(map(float, vec)) for vec in vectors]
        except Exception as e:
            logger.error(f"Local embeddings error: {e}")
            return [[0.0] * 384 for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        try:
            vec = self.fn([text])[0]
            return list(map(float, vec))
        except Exception as e:
            logger.error(f"Local query embedding error: {e}")
            return [0.0] * 384

def get_embeddings_model() -> Embeddings:
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and not settings.OPENAI_API_KEY.startswith("your_"):
        return OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL
        )
    else:
        return LocalChromaEmbeddings()

def get_vector_store() -> Chroma:
    embeddings = get_embeddings_model()
    os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
    
    vector_store = Chroma(
        collection_name="research_documents",
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIRECTORY
    )
    return vector_store

