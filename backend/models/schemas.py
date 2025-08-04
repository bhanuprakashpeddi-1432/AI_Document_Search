from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import hashlib


class QueryRequest(BaseModel):
    """Request model for the /hackrx/run endpoint"""
    documents: str  # URL to the document
    questions: List[str]  # List of questions to ask

    def get_document_hash(self) -> str:
        """Generate a hash for the document URL for caching purposes"""
        return hashlib.sha256(self.documents.encode()).hexdigest()


class SourceChunk(BaseModel):
    """Model for source chunks with traceability"""
    text: str
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    score: Optional[float] = None


class QueryResponse(BaseModel):
    """Response model for the /hackrx/run endpoint"""
    answers: List[str]
    sources: Optional[List[List[SourceChunk]]] = None  # Sources for each answer
    processing_time: Optional[float] = None
    document_hash: Optional[str] = None


class DocumentChunk(BaseModel):
    """Internal model for document chunks"""
    id: str
    text: str
    page_number: Optional[int] = None
    chunk_type: str = "text"  # "text" or "table"
    metadata: Optional[dict] = None


class SubQuestion(BaseModel):
    """Model for decomposed sub-questions"""
    question: str
    context_needed: Optional[str] = None
    priority: Optional[int] = 1
