import os
import tempfile
import pytest
from app.rag.document_processor import DocumentProcessor
from app.tools.rag_retriever import RAGRetrieverTool

def test_rag_ingest_and_retrieve():
    # Create temporary text file
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Project Requirements: The AI application requires ChromaDB vector database for local persistence and candidate resume filtering.\n")
        f.write("All resume processing must complete within 200ms per candidate.\n")
        temp_path = f.name

    try:
        processor = DocumentProcessor()
        doc_id = "test-doc-123"
        chunk_count = processor.process_and_index_file(
            file_path=temp_path,
            document_id=doc_id,
            original_filename="sample_requirements.txt"
        )
        assert chunk_count > 0

        # Retrieve
        retriever = RAGRetrieverTool()
        results = retriever.retrieve("What vector database is required by the project?", k=10)
        assert len(results) > 0
        assert any("sample_requirements.txt" in res["source"] for res in results)

        # Clean up vectors
        processor.delete_document_chunks(doc_id)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
