"""Schemas para el agente RAG y documentos vectoriales."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    historial: list[ChatMessage] | None = None


class ChatResponse(BaseModel):
    respuesta: str


class DocumentoIngestRequest(BaseModel):
    ref_tipo: str
    ref_id: int | None = None
    titulo: str
    contenido: str


class DocumentoIngestResponse(BaseModel):
    ref_tipo: str
    ref_id: int | None = None
    titulo: str


class DocumentoSearchRequest(BaseModel):
    query: str
    ref_tipo: str | None = None
    k: int = 5


class DocumentoSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ref_tipo: str
    ref_id: int | None = None
    titulo: str
    contenido: str
    similarity: float


class NotaMedicaIngestRequest(BaseModel):
    """Ingesta automática de una nota médica existente por su cita_id."""
    cita_id: int


class HealthCheck(BaseModel):
    ollama: str
    embedding_model: str
    llm_model: str
    vector_count: int
