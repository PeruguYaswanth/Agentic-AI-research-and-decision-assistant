import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from rank_bm25 import BM25Okapi

from app.config import settings

logger = logging.getLogger(__name__)

def bm25_tokenize(text: str) -> List[str]:
    """
    Lightweight tokenizer preserving numbers, percentages, currency, dates, and alphanumeric codes.
    """
    if not text:
        return []
    # Tokenize words, numbers, and technical terms
    tokens = re.findall(r"[a-zA-Z0-9\$\%_\.\-]+", text.lower())
    # Filter very short meaningless punctuation tokens
    return [t for t in tokens if len(t) > 1 or t.isdigit()]

class BM25Indexer:
    """
    Lightweight, in-memory + JSON-persisted BM25 lexical search index.
    Zero C/Rust external dependencies, fast execution, Render 512MB RAM friendly.
    """
    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = persist_path or os.path.join(settings.CHROMA_PERSIST_DIRECTORY, "bm25_corpus.json")
        self.documents: List[Dict[str, Any]] = []
        self.corpus_tokens: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self._load_from_disk()

    def _load_from_disk(self):
        try:
            if os.path.exists(self.persist_path):
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                if self.documents:
                    self.corpus_tokens = [bm25_tokenize(d.get("content", "")) for d in self.documents]
                    self.bm25 = BM25Okapi(self.corpus_tokens)
                    logger.info(f"Loaded {len(self.documents)} BM25 corpus chunks from {self.persist_path}")
        except Exception as e:
            logger.warning(f"Failed to load BM25 index from disk: {e}")
            self.documents = []
            self.corpus_tokens = []
            self.bm25 = None

    def _save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save BM25 index to disk: {e}")

    def add_documents(self, docs: List[Dict[str, Any]]):
        """
        Adds a batch of document chunk dictionaries to the BM25 index.
        Each doc should have chunk_id, content, and metadata.
        """
        existing_ids = {d["chunk_id"] for d in self.documents}
        new_docs = [d for d in docs if d["chunk_id"] not in existing_ids]

        if not new_docs:
            return

        self.documents.extend(new_docs)
        self.corpus_tokens = [bm25_tokenize(d.get("content", "")) for d in self.documents]
        self.bm25 = BM25Okapi(self.corpus_tokens)
        self._save_to_disk()

    def delete_document(self, document_id: str):
        """Removes all chunks associated with a document_id."""
        initial_len = len(self.documents)
        self.documents = [
            d for d in self.documents
            if d.get("metadata", {}).get("document_id") != document_id
        ]
        if len(self.documents) != initial_len:
            if self.documents:
                self.corpus_tokens = [bm25_tokenize(d.get("content", "")) for d in self.documents]
                self.bm25 = BM25Okapi(self.corpus_tokens)
            else:
                self.corpus_tokens = []
                self.bm25 = None
            self._save_to_disk()

    def search(
        self,
        query: str,
        top_k: int = 8,
        document_id: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Performs BM25 lexical matching against indexed chunks.
        Returns list of (doc_dict, normalized_score).
        """
        if not self.bm25 or not self.documents:
            return []

        tokens = bm25_tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)
        max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0

        results: List[Tuple[Dict[str, Any], float]] = []
        for doc, score in zip(self.documents, scores):
            if score <= 0.01:
                continue

            doc_meta = doc.get("metadata", {})
            if document_id and doc_meta.get("document_id") != document_id:
                continue

            normalized_score = float(score / max_score)
            results.append((doc, normalized_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

_bm25_instance: Optional[BM25Indexer] = None

def get_bm25_indexer() -> BM25Indexer:
    global _bm25_instance
    if _bm25_instance is None:
        _bm25_instance = BM25Indexer()
    return _bm25_instance
