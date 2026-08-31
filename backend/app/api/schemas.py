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
    tool_used: Optional[str] = None




class StudyRequest(BaseModel):
    query: str
    count: Optional[int] = None


class StudySource(BaseModel):
    document: str
    page: Optional[int] = None


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: int
    explanation: str


class QuizResponse(BaseModel):
    topic: str
    questions: List[QuizQuestion]
    sources: List[StudySource]
    count: int


class Flashcard(BaseModel):
    front: str
    back: str


class FlashcardsResponse(BaseModel):
    topic: str
    cards: List[Flashcard]
    sources: List[StudySource]
    count: int
