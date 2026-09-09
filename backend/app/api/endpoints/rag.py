"""RAG agent endpoints and vector document management."""

import json
from typing import Any

from core.agent import chat_con_agente, chat_con_agente_stream
from core.config import settings
from core.rag import ingest_document, search_documents
from dependencies import get_current_user, get_db
from dependencies_i18n import I18nResponse, get_language
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from models.user import User as UserModel
from schemas.rag import (
    ChatRequest,
    ChatResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentSearchRequest,
    DocumentSearchResult,
    HealthCheck,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["RAG & AI Agent"])


@router.get(
    "/rag/health",
    response_model=HealthCheck,
    summary="Check Ollama and pgvector status",
)
async def rag_health(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Checks that Ollama is accessible and how many vectorized documents exist."""
    import httpx

    ollama_status = "unreachable"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                ollama_status = "ok"
    except Exception:
        pass

    result = await db.execute(text("SELECT COUNT(*) FROM vector_documents"))
    vector_count = result.scalar() or 0

    return HealthCheck(
        ollama=ollama_status,
        embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
        llm_model=settings.OLLAMA_LLM_MODEL,
        vector_count=vector_count,
    )


@router.post(
    "/rag/ingest",
    response_model=DocumentIngestResponse,
    status_code=201,
    summary="Ingest a document into the vector store",
)
async def ingest(
    *,
    db: AsyncSession = Depends(get_db),
    doc_in: DocumentIngestRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Generates embedding with Ollama and saves the document in pgvector."""
    i18n = I18nResponse(language)
    try:
        result = await ingest_document(
            db,
            reference_type=doc_in.reference_type,
            reference_id=doc_in.reference_id,
            title=doc_in.title,
            content=doc_in.content,
        )
        return result
    except Exception:
        raise i18n.error("internal_error", status_code=500)


@router.post(
    "/rag/ingest-note/{appointment_id}",
    status_code=201,
    summary="Ingest an existing medical note into the vector store",
)
async def ingest_medical_note(
    *,
    db: AsyncSession = Depends(get_db),
    appointment_id: int,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Finds the medical note of an appointment and indexes it vectorially."""
    i18n = I18nResponse(language)
    result = await db.execute(
        text(
            "SELECT id, diagnosis, treatment, observations "
            "FROM medical_notes WHERE appointment_id = :appointment_id"
        ),
        {"appointment_id": appointment_id},
    )
    note = result.mappings().first()
    if not note:
        raise i18n.error("note_not_found", status_code=404)

    content_parts = [f"Diagnosis: {note['diagnosis']}"]
    if note["treatment"]:
        content_parts.append(f"Treatment: {note['treatment']}")
    if note["observations"]:
        content_parts.append(f"Observations: {note['observations']}")
    content = "\n".join(content_parts)

    doc_result = await ingest_document(
        db,
        reference_type="MEDICAL_NOTE",
        reference_id=note["id"],
        title=f"Medical note appointment #{appointment_id}",
        content=content,
    )
    return doc_result


@router.post(
    "/rag/search",
    response_model=list[DocumentSearchResult],
    summary="Search documents by semantic similarity",
)
async def search(
    *,
    db: AsyncSession = Depends(get_db),
    search_in: DocumentSearchRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Performs embedding search over vectorized documents."""
    i18n = I18nResponse(language)
    try:
        results = await search_documents(
            db, search_in.query, k=search_in.k, reference_type=search_in.reference_type
        )
        return results
    except Exception:
        raise i18n.error("search_error", status_code=500)


@router.post(
    "/rag/chat",
    response_model=ChatResponse,
    summary="Chat with the MedAssist agent (RAG + tool calling)",
)
async def chat(
    *,
    db: AsyncSession = Depends(get_db),
    chat_in: ChatRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> ChatResponse:
    """Sends a message to the agent that can query the DB and vectorized documents."""
    i18n = I18nResponse(language)
    history = None
    if chat_in.history:
        history = [{"role": m.role, "content": m.content} for m in chat_in.history]

    try:
        response = await chat_con_agente(
            chat_in.message,
            conn_str=settings.DATABASE_URL,
            history=history,
        )
        return ChatResponse(response=response)
    except Exception:
        raise i18n.error("agent_error", status_code=500)


@router.post(
    "/rag/chat/stream",
    summary="Chat with the MedAssist agent (streaming SSE)",
)
async def chat_stream(
    *,
    db: AsyncSession = Depends(get_db),
    chat_in: ChatRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> StreamingResponse:
    """Streams agent response token-by-token using Server-Sent Events."""
    i18n = I18nResponse(language)
    history = None
    if chat_in.history:
        history = [{"role": m.role, "content": m.content} for m in chat_in.history]

    async def event_generator():
        try:
            async for chunk in chat_con_agente_stream(
                chat_in.message,
                conn_str=settings.DATABASE_URL,
                history=history,
            ):
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'error': i18n.get('agent_error')})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
