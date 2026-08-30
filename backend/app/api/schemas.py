from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    title: Optional[str] = None
    file_type: str
    content: str
    status: str
    size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class SearchResultMetadata(BaseModel):
    document_id: Optional[int] = None
    chunk_index: Optional[int] = None
    page: Optional[int] = None


class SearchResult(BaseModel):
    document: str
    relevant_text: str
    score: float
    metadata: SearchResultMetadata


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatSource(BaseModel):
    document: str
    page: Optional[int] = None
    relevance: float


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource]
    conversation_id: int
    # Which agent tool handled this message (e.g. "SEARCH_KNOWLEDGE",
    # "STUDY_ASSISTANT"). Purely informational — the frontend doesn't need
    # to know about it, but it's handy for the dev console / a demo.
    tool_used: Optional[str] = None
