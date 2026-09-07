"""Schemas for the RAG agent and vector documents."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] | None = None


class ChatResponse(BaseModel):
    response: str


class DocumentIngestRequest(BaseModel):
    reference_type: str
    reference_id: int | None = None
    title: str
    content: str


class DocumentIngestResponse(BaseModel):
    reference_type: str
    reference_id: int | None = None
    title: str


class DocumentSearchRequest(BaseModel):
    query: str
    reference_type: str | None = None
    k: int = 5


class DocumentSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_type: str
    reference_id: int | None = None
    title: str
    content: str
    similarity: float


class MedicalNoteIngestRequest(BaseModel):
    """Automatic ingestion of an existing medical note by its appointment_id."""
    appointment_id: int


class HealthCheck(BaseModel):
    ollama: str
    embedding_model: str
    llm_model: str
    vector_count: int
