import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional
from app.rag.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_hybrid_retriever() -> HybridRetriever:
    return HybridRetriever()

class RAGRetrieverTool:
    """
    RAG Retriever Tool utilizing Hybrid (Vector + BM25) retrieval with document isolation.
    """
    @property
    def hybrid_retriever(self) -> HybridRetriever:
        return get_hybrid_retriever()

    def retrieve(
        self,
        query: str,
        k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant document chunks from ChromaDB + BM25 index.
        Optionally isolates retrieval to a specific document_id.
        """
        try:
            return self.hybrid_retriever.retrieve(
                query=query,
                top_k=k,
                document_id=document_id,
                include_neighbors=True
            )
        except Exception as e:
            logger.error(f"Error executing hybrid RAG retrieval for query '{query}': {e}")
            return []
