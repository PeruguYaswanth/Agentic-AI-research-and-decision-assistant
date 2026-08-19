import os
import uuid
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.rag.vector_store import get_vector_store

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        self.vector_store = get_vector_store()

    def process_and_index_file(self, file_path: str, document_id: str, original_filename: str) -> int:
        """
        Loads a document (PDF, TXT, MD), splits into chunks, tags with metadata, and indexes into ChromaDB.
        Returns the number of created chunks.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        documents: List[Document] = []

        if file_ext == ".pdf":
            loader = PyPDFLoader(file_path)
            raw_docs = loader.load()
            for doc in raw_docs:
                page_num = doc.metadata.get("page", 0) + 1
                doc.metadata.update({
                    "document_id": document_id,
                    "filename": original_filename,
                    "page_number": page_num,
                    "source": original_filename
                })
                documents.append(doc)
        else:
            loader = TextLoader(file_path, encoding="utf-8")
            raw_docs = loader.load()
            for doc in raw_docs:
                doc.metadata.update({
                    "document_id": document_id,
                    "filename": original_filename,
                    "page_number": 1,
                    "source": original_filename
                })
                documents.append(doc)

        if not documents:
            return 0

        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk index metadata
        for idx, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = idx
            chunk.metadata["chunk_id"] = f"{document_id}_{idx}"

        # Index into ChromaDB
        self.vector_store.add_documents(chunks)
        return len(chunks)

    def delete_document_chunks(self, document_id: str):
        """
        Deletes all vector store entries corresponding to document_id.
        """
        try:
            # Chroma DB delete by metadata filter
            self.vector_store.delete(where={"document_id": document_id})
        except Exception as e:
            # Handle potential chroma API variations gracefully
            print(f"Error removing document vectors for {document_id}: {str(e)}")
