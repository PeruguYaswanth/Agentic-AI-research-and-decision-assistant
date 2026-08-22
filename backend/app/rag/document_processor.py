import os
import re
import uuid
import logging
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

from app.rag.document_cleaner import DocumentCleaner
from app.rag.vector_store import get_vector_store
from app.rag.bm25_indexer import get_bm25_indexer

logger = logging.getLogger(__name__)

HEADING_PATTERNS = [
    re.compile(r"^#{1,4}\s+(.+)$"),  # Markdown headers
    re.compile(r"^(?:Section\s+\d+|[0-9]+(?:\.[0-9]+)*)\s*[:\.\-]?\s+(.+)$", re.IGNORECASE),  # Numbered sections
    re.compile(r"^([A-Z0-9\s,\-:\(\)\/\&]{4,60})$"),  # All-caps headings
    re.compile(r"^([A-Z][a-zA-Z0-9\s,\-:\(\)\/\&]{3,60}\s+(?:Policy|Procedure|Guidelines|Entitlement|Allowance|Requirements|Overview|Schedule|Agreement|Terms|Summary|Definitions|Compensation|Benefits|Leave|Insurance|Termination|Probation|Standards|Obligations)):?$", re.IGNORECASE)
]

def is_potential_heading(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped or len(stripped) > 75:
        return None

    # Check if line matches known heading patterns
    for pat in HEADING_PATTERNS:
        m = pat.match(stripped)
        if m:
            heading = m.group(1) if m.groups() else stripped
            # Filter out lines that end with a period and look like normal sentences
            if not stripped.endswith(".") or stripped.startswith("#"):
                return heading.strip("# :.-")

    # Short line in Title Case without terminal punctuation
    words = stripped.split()
    if 1 <= len(words) <= 6 and all(w[0].isupper() for w in words if w.isalpha()) and not stripped.endswith("."):
        return stripped

    return None

class DocumentProcessor:
    """
    Structure-aware document processor.
    Splits text along section/paragraph boundaries, attaches headings,
    injects contextual headers, and indexes into ChromaDB and BM25.
    """
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_store = get_vector_store()
        self.bm25_indexer = get_bm25_indexer()

    def process_and_index_file(
        self,
        file_path: str,
        document_id: str,
        original_filename: str,
        upload_id: Optional[str] = None
    ) -> int:
        """
        Loads document, performs structure-aware chunking, injects contextual metadata,
        and indexes into ChromaDB vector store + BM25 indexer.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == ".pdf":
            pages_data = DocumentCleaner.extract_and_clean_pdf(file_path)
        else:
            pages_data = DocumentCleaner.extract_and_clean_text(file_path)

        if not pages_data:
            logger.warning(f"No text extracted from file: {original_filename}")
            return 0

        # Structure-aware chunk generation
        chunks: List[Document] = self._create_structure_aware_chunks(
            pages_data=pages_data,
            document_id=document_id,
            original_filename=original_filename,
            upload_id=upload_id or str(uuid.uuid4())
        )

        if not chunks:
            logger.warning(f"0 chunks created for: {original_filename}")
            return 0

        # 1. Index into ChromaDB
        self.vector_store.add_documents(chunks)

        # 2. Index into lightweight BM25 index
        bm25_docs = [
            {
                "chunk_id": c.metadata["chunk_id"],
                "content": c.page_content,
                "raw_text": c.metadata.get("raw_text", c.page_content),
                "metadata": c.metadata
            }
            for c in chunks
        ]
        self.bm25_indexer.add_documents(bm25_docs)

        logger.info(f"Indexed {len(chunks)} chunks for document '{original_filename}' ({document_id}) into Chroma & BM25.")
        return len(chunks)

    def _create_structure_aware_chunks(
        self,
        pages_data: List[Dict[str, Any]],
        document_id: str,
        original_filename: str,
        upload_id: str
    ) -> List[Document]:
        documents: List[Document] = []
        global_chunk_idx = 0
        current_section = "General"

        for page_info in pages_data:
            page_num = page_info["page_number"]
            page_text = page_info["text"]

            # Break page into structural blocks / paragraphs
            blocks = re.split(r"\n\s*\n", page_text)

            current_chunk_paragraphs: List[str] = []
            current_chunk_len = 0

            for block in blocks:
                block_clean = block.strip()
                if not block_clean:
                    continue

                # Check if block is or starts with a heading
                first_line = block_clean.split("\n")[0]
                detected_heading = is_potential_heading(first_line)

                if detected_heading:
                    current_section = detected_heading

                # Check if adding this block exceeds target chunk size
                block_len = len(block_clean)
                if current_chunk_paragraphs and (current_chunk_len + block_len > self.chunk_size):
                    raw_chunk_text = "\n\n".join(current_chunk_paragraphs).strip()
                    if raw_chunk_text:
                        doc = self._build_contextual_document(
                            raw_text=raw_chunk_text,
                            document_id=document_id,
                            document_name=original_filename,
                            page_number=page_num,
                            section=current_section,
                            chunk_index=global_chunk_idx,
                            upload_id=upload_id
                        )
                        documents.append(doc)
                        global_chunk_idx += 1

                    # Keep last paragraph for overlap context if applicable
                    if len(current_chunk_paragraphs) > 1 and len(current_chunk_paragraphs[-1]) <= self.chunk_overlap * 2:
                        current_chunk_paragraphs = [current_chunk_paragraphs[-1], block_clean]
                        current_chunk_len = len(current_chunk_paragraphs[0]) + block_len + 2
                    else:
                        current_chunk_paragraphs = [block_clean]
                        current_chunk_len = block_len
                else:
                    current_chunk_paragraphs.append(block_clean)
                    current_chunk_len += block_len + 2

            # Flush any remaining paragraphs on this page
            if current_chunk_paragraphs:
                raw_chunk_text = "\n\n".join(current_chunk_paragraphs).strip()
                if raw_chunk_text:
                    doc = self._build_contextual_document(
                        raw_text=raw_chunk_text,
                        document_id=document_id,
                        document_name=original_filename,
                        page_number=page_num,
                        section=current_section,
                        chunk_index=global_chunk_idx,
                        upload_id=upload_id
                    )
                    documents.append(doc)
                    global_chunk_idx += 1

        return documents

    def _build_contextual_document(
        self,
        raw_text: str,
        document_id: str,
        document_name: str,
        page_number: int,
        section: str,
        chunk_index: int,
        upload_id: str
    ) -> Document:
        chunk_id = f"{document_id}_{chunk_index}"
        
        # Contextual Framing: inject metadata header into the embedded content
        contextual_content = (
            f"Document: {document_name}\n"
            f"Section: {section}\n"
            f"Page: {page_number}\n\n"
            f"{raw_text}"
        )

        metadata = {
            "document_id": document_id,
            "document_name": document_name,
            "filename": document_name,
            "page_number": page_number,
            "section": section,
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "upload_id": upload_id,
            "raw_text": raw_text,
            "source": f"{document_name} (Page {page_number})"
        }

        return Document(
            page_content=contextual_content,
            metadata=metadata
        )

    def delete_document_chunks(self, document_id: str):
        """
        Deletes all vector store and BM25 entries corresponding to document_id.
        """
        try:
            self.vector_store.delete(where={"document_id": document_id})
        except Exception as e:
            logger.warning(f"Error removing vector chunks for {document_id}: {e}")

        try:
            self.bm25_indexer.delete_document(document_id)
        except Exception as e:
            logger.warning(f"Error removing BM25 chunks for {document_id}: {e}")
