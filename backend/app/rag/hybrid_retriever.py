import re
import logging
from functools import lru_cache
from typing import List, Dict, Any, Optional
from app.config import settings
from app.rag.vector_store import get_vector_store
from app.rag.bm25_indexer import get_bm25_indexer

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_reranker_model():
    """
    Optional lazy loaded CrossEncoder model.
    Only loaded if ENABLE_RERANKER=True.
    """
    logger.info("Loading CrossEncoder reranker model on CPU...")
    from sentence_transformers import CrossEncoder
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")
    logger.info("CrossEncoder reranker model loaded.")
    return reranker

def preprocess_query(query: str) -> List[str]:
    """
    Cleans the query and decomposes multi-part compound queries into sub-queries.
    Example: "What is notice period, salary, and leave policy?" -> ["notice period", "salary", "leave policy", full_query]
    """
    clean_q = re.sub(r"[^\w\s\$\%\-\.\:\?]", " ", query).strip()
    sub_queries = [clean_q]

    # Check for multi-part conjunctions (comma separated or 'and', 'also', 'as well as')
    if any(sep in query.lower() for sep in [",", " and ", " as well as ", " versus ", " vs "]):
        # Extract potential sub-clause phrases
        parts = re.split(r",|\band\b|\bas well as\b", query, flags=re.IGNORECASE)
        for p in parts:
            p_strip = p.strip()
            # Clean question words from sub-parts
            for qw in ["what is the", "what are the", "what is", "what are", "tell me about", "details on", "explain", "how much is"]:
                if p_strip.lower().startswith(qw):
                    p_strip = p_strip[len(qw):].strip()
            if len(p_strip) > 3 and p_strip not in sub_queries:
                sub_queries.append(p_strip)

    return sub_queries

class HybridRetriever:
    """
    Lightweight, high-accuracy hybrid retriever combining:
    1. Vector Similarity Search (ChromaDB)
    2. BM25 Lexical Keyword Search (BM25Okapi)
    3. Multi-Query Dissection
    4. Reciprocal Rank Fusion & Score Normalization
    5. Neighboring Chunk Context Expansion
    6. Optional Cross-Encoder Reranking (if ENABLE_RERANKER=true)
    """
    @property
    def vector_store(self):
        return get_vector_store()

    @property
    def bm25_indexer(self):
        return get_bm25_indexer()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        vector_top_k: int = 8,
        bm25_top_k: int = 8,
        document_id: Optional[str] = None,
        include_neighbors: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval and returns top ranked chunks.
        """
        sub_queries = preprocess_query(query)
        candidate_map: Dict[str, Dict[str, Any]] = {}
        score_tracker: Dict[str, Dict[str, float]] = {}

        for sub_q in sub_queries:
            # 1. Vector Search
            try:
                filter_dict = {"document_id": document_id} if document_id else None
                if filter_dict:
                    vec_results = self.vector_store.similarity_search_with_score(sub_q, k=vector_top_k, filter=filter_dict)
                else:
                    vec_results = self.vector_store.similarity_search_with_score(sub_q, k=vector_top_k)

                for rank, (doc, dist) in enumerate(vec_results, start=1):
                    meta = doc.metadata or {}
                    chunk_id = meta.get("chunk_id") or f"{meta.get('document_id', 'doc')}_{meta.get('chunk_index', rank)}"
                    
                    # Convert distance to normalized similarity score (cosine distance in Chroma is typically 0 to 2)
                    sim_score = max(0.0, 1.0 - (float(dist) / 2.0))

                    if chunk_id not in candidate_map:
                        candidate_map[chunk_id] = {
                            "chunk_id": chunk_id,
                            "content": doc.page_content,
                            "raw_text": meta.get("raw_text", doc.page_content),
                            "filename": meta.get("filename") or meta.get("document_name", "Uploaded Document"),
                            "page_number": meta.get("page_number", 1),
                            "section": meta.get("section", "General"),
                            "chunk_index": meta.get("chunk_index", 0),
                            "document_id": meta.get("document_id"),
                            "source": f"{meta.get('filename', 'Document')} (Page {meta.get('page_number', 1)})",
                            "type": "rag"
                        }
                        score_tracker[chunk_id] = {"vec_score": 0.0, "bm25_score": 0.0, "rrf_rank": 0.0}

                    score_tracker[chunk_id]["vec_score"] = max(score_tracker[chunk_id]["vec_score"], sim_score)
                    score_tracker[chunk_id]["rrf_rank"] += 1.0 / (60 + rank)
            except Exception as e:
                logger.debug(f"Vector search warning for sub_query '{sub_q}': {e}")

            # 2. BM25 Lexical Search
            try:
                bm25_results = self.bm25_indexer.search(sub_q, top_k=bm25_top_k, document_id=document_id)
                for rank, (doc_dict, bm25_score) in enumerate(bm25_results, start=1):
                    chunk_id = doc_dict["chunk_id"]
                    meta = doc_dict.get("metadata", {})

                    if chunk_id not in candidate_map:
                        candidate_map[chunk_id] = {
                            "chunk_id": chunk_id,
                            "content": doc_dict.get("content", ""),
                            "raw_text": doc_dict.get("raw_text") or meta.get("raw_text", doc_dict.get("content", "")),
                            "filename": meta.get("filename") or meta.get("document_name", "Uploaded Document"),
                            "page_number": meta.get("page_number", 1),
                            "section": meta.get("section", "General"),
                            "chunk_index": meta.get("chunk_index", 0),
                            "document_id": meta.get("document_id"),
                            "source": f"{meta.get('filename', 'Document')} (Page {meta.get('page_number', 1)})",
                            "type": "rag"
                        }
                        score_tracker[chunk_id] = {"vec_score": 0.0, "bm25_score": 0.0, "rrf_rank": 0.0}

                    score_tracker[chunk_id]["bm25_score"] = max(score_tracker[chunk_id]["bm25_score"], bm25_score)
                    score_tracker[chunk_id]["rrf_rank"] += 1.0 / (60 + rank)
            except Exception as e:
                logger.debug(f"BM25 search warning for sub_query '{sub_q}': {e}")

        if not candidate_map:
            return []

        # 3. Hybrid Score Fusion
        # Combined score: 0.65 * Vector + 0.35 * BM25 + RRF Boost
        scored_candidates = []
        for chunk_id, chunk_data in candidate_map.items():
            scores = score_tracker[chunk_id]
            v_s = scores["vec_score"]
            b_s = scores["bm25_score"]
            rrf = scores["rrf_rank"]

            # Weighted linear combination
            fused_score = (0.65 * v_s) + (0.35 * b_s) + (rrf * 10.0)
            chunk_data["similarity_score"] = float(fused_score)
            scored_candidates.append((fused_score, chunk_data))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [c for _, c in scored_candidates[:top_k * 2]]

        # Optional CrossEncoder Reranking if explicitly enabled
        if settings.ENABLE_RERANKER and top_candidates:
            try:
                reranker = get_reranker_model()
                pairs = [[query, c.get("raw_text") or c.get("content", "")] for c in top_candidates]
                cross_scores = reranker.predict(pairs)
                for c, s in zip(top_candidates, cross_scores):
                    c["similarity_score"] = float(s)
                top_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
            except Exception as e:
                logger.warning(f"Reranking error, falling back to fused score: {e}")

        top_selected = top_candidates[:top_k]

        # 4. Optional Neighboring Chunk Context Expansion
        if include_neighbors and top_selected:
            expanded_selected = list(top_selected)
            selected_ids = {c["chunk_id"] for c in top_selected}

            # Check top 2 chunks for adjacent chunks in the same section
            for top_c in top_selected[:2]:
                doc_id = top_c.get("document_id")
                curr_idx = top_c.get("chunk_index", 0)
                sec = top_c.get("section")
                
                # Check next chunk index
                next_chunk_id = f"{doc_id}_{curr_idx + 1}"
                if next_chunk_id not in selected_ids and next_chunk_id in self.bm25_indexer.documents:
                    # Find chunk
                    neighbor = next((d for d in self.bm25_indexer.documents if d.get("chunk_id") == next_chunk_id), None)
                    if neighbor and neighbor.get("metadata", {}).get("section") == sec:
                        n_meta = neighbor.get("metadata", {})
                        expanded_selected.append({
                            "chunk_id": next_chunk_id,
                            "content": neighbor.get("content", ""),
                            "raw_text": neighbor.get("raw_text", ""),
                            "filename": n_meta.get("filename", top_c.get("filename")),
                            "page_number": n_meta.get("page_number", top_c.get("page_number")),
                            "section": sec,
                            "chunk_index": curr_idx + 1,
                            "document_id": doc_id,
                            "source": f"{top_c.get('filename')} (Page {n_meta.get('page_number', top_c.get('page_number'))})",
                            "type": "rag",
                            "similarity_score": top_c["similarity_score"] * 0.9
                        })
                        selected_ids.add(next_chunk_id)

            top_selected = expanded_selected[:top_k + 1]

        return top_selected
