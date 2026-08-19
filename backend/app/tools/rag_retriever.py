import logging
from typing import List, Dict, Any, Optional
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

class RAGRetrieverTool:
    def __init__(self):
        self.vector_store = get_vector_store()

    def retrieve(self, query: str, k: int = 4, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant document chunks from ChromaDB vector store.
        Optionally filters by document_id.
        Returns list of dicts with content, filename, page_number, similarity_score, source.
        """
        try:
            filter_dict = {"document_id": document_id} if document_id else None
            if filter_dict:
                results_with_score = self.vector_store.similarity_search_with_score(query, k=k, filter=filter_dict)
            else:
                results_with_score = self.vector_store.similarity_search_with_score(query, k=k)

            retrieved_chunks = []
            for doc, score in results_with_score:
                metadata = doc.metadata or {}
                filename = metadata.get("filename", "Uploaded Document")
                page_num = metadata.get("page_number", 1)
                
                retrieved_chunks.append({
                    "content": doc.page_content,
                    "filename": filename,
                    "page_number": page_num,
                    "similarity_score": float(score),
                    "source": f"{filename} (Page {page_num})" if page_num else filename,
                    "document_id": metadata.get("document_id"),
                    "type": "rag"
                })
            return retrieved_chunks
        except Exception as e:
            logger.error(f"Error executing RAG vector search for query '{query}': {e}")
            return []

