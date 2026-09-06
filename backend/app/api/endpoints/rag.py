"""RAG agent endpoints and vector document management."""

from typing import Any

from core.agent import chat_con_agente
from core.config import settings
from core.rag import ingest_documento, search_documentos
from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException
from models.user import User as UserModel
from schemas.rag import (
    ChatRequest,
    ChatResponse,
    DocumentoIngestRequest,
    DocumentoIngestResponse,
    DocumentoSearchRequest,
    DocumentoSearchResult,
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

    result = await db.execute(text("SELECT COUNT(*) FROM documentos_vectoriales"))
    vector_count = result.scalar() or 0

    return HealthCheck(
        ollama=ollama_status,
        embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
        llm_model=settings.OLLAMA_LLM_MODEL,
        vector_count=vector_count,
    )


@router.post(
    "/rag/ingest",
    response_model=DocumentoIngestResponse,
    status_code=201,
    summary="Ingest a document into the vector store",
)
async def ingest(
    *,
    db: AsyncSession = Depends(get_db),
    doc_in: DocumentoIngestRequest,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Generates embedding with Ollama and saves the document in pgvector."""
    try:
        result = await ingest_documento(
            db,
            ref_tipo=doc_in.ref_tipo,
            ref_id=doc_in.ref_id,
            titulo=doc_in.titulo,
            contenido=doc_in.contenido,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error ingesting document: {exc}"
        )


@router.post(
    "/rag/ingest-nota/{cita_id}",
    status_code=201,
    summary="Ingest an existing medical note into the vector store",
)
async def ingest_nota_medica(
    *,
    db: AsyncSession = Depends(get_db),
    cita_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Finds the medical note of an appointment and indexes it vectorially."""
    result = await db.execute(
        text(
            "SELECT id, diagnostico, tratamiento, observaciones "
            "FROM notas_medicas WHERE cita_id = :cita_id"
        ),
        {"cita_id": cita_id},
    )
    nota = result.mappings().first()
    if not nota:
        raise HTTPException(status_code=404, detail="Medical note not found.")

    contenido_parts = [f"Diagnosis: {nota['diagnostico']}"]
    if nota["tratamiento"]:
        contenido_parts.append(f"Treatment: {nota['tratamiento']}")
    if nota["observaciones"]:
        contenido_parts.append(f"Observations: {nota['observaciones']}")
    contenido = "\n".join(contenido_parts)

    doc_result = await ingest_documento(
        db,
        ref_tipo="NOTA_MEDICA",
        ref_id=nota["id"],
        titulo=f"Medical note appointment #{cita_id}",
        contenido=contenido,
    )
    return doc_result


@router.post(
    "/rag/search",
    response_model=list[DocumentoSearchResult],
    summary="Search documents by semantic similarity",
)
async def search(
    *,
    db: AsyncSession = Depends(get_db),
    search_in: DocumentoSearchRequest,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Performs embedding search over vectorized documents."""
    try:
        results = await search_documentos(
            db, search_in.query, k=search_in.k, ref_tipo=search_in.ref_tipo
        )
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search error: {exc}")


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
) -> ChatResponse:
    """Sends a message to the agent that can query the DB and vectorized documents."""
    historial = None
    if chat_in.historial:
        historial = [{"role": m.role, "content": m.content} for m in chat_in.historial]

    try:
        respuesta = await chat_con_agente(
            chat_in.message,
            conn_str=settings.DATABASE_URL,
            historial=historial,
        )
        return ChatResponse(respuesta=respuesta)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")
