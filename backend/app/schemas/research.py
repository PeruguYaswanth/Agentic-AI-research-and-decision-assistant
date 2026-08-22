from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class ChatRequest(BaseModel):
    question: str = Field(..., description="User research question")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")

class SourceItem(BaseModel):
    title: str
    url: Optional[str] = None
    snippet: Optional[str] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    authority_score: Optional[float] = None
    source: str = "web"  # web or rag

class ExecutionStep(BaseModel):
    step_name: str
    status: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ResearchResponse(BaseModel):
    session_id: str
    conversation_id: str
    question: str
    plan: Optional[List[str]] = None
    final_answer: str
    confidence_level: Optional[str] = "HIGH"  # HIGH, MEDIUM, LOW
    confidence_reason: Optional[str] = None
    key_findings: Optional[List[str]] = None
    freshness_category: Optional[str] = "REAL_TIME"
    sources: List[SourceItem] = []
    execution_logs: List[ExecutionStep] = []
    status: str = "completed"

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    indexed_status: str
    uploaded_at: datetime

class HistorySessionResponse(BaseModel):
    session_id: str
    conversation_id: str
    question: str
    final_answer: Optional[str] = None
    created_at: datetime
    sources_count: int

class RAGQueryRequest(BaseModel):
    question: str = Field(..., description="Question to answer using uploaded document knowledge base")
    document_id: Optional[str] = Field(None, description="Specific document ID to query against, or None for all documents")
    top_k: int = Field(default=4, description="Number of document chunks to retrieve")

class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    document_id: Optional[str] = None
    sources: List[SourceItem] = []
