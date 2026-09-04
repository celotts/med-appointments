"""Endpoints del agente RAG y gestión de documentos vectoriales."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db, get_current_user
from core.config import settings
from core.rag import ingest_documento, search_documentos
from core.agent import chat_con_agente
from models.user import User as UserModel
from schemas.rag import (
    ChatRequest,
    ChatResponse,
    DocumentoIngestRequest,
    DocumentoIngestResponse,
    DocumentoSearchRequest,
    DocumentoSearchResult,
    HealthCheck,
    NotaMedicaIngestRequest,
)

router = APIRouter(prefix="/api/v1", tags=["RAG & AI Agent"])


@router.get(
    "/rag/health",
    response_model=HealthCheck,
    summary="Verificar estado de Ollama y pgvector",
)
async def rag_health(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Verifica que Ollama esté accesible y cuántos documentos vectorizados hay."""
    import httpx

    ollama_status = "unreachable"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                ollama_status = "ok"
    except Exception:
        pass

    result = await db.execute(
        text("SELECT COUNT(*) FROM documentos_vectoriales")
    )
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
    summary="Ingestar un documento al almacén vectorial",
)
async def ingest(
    *,
    db: AsyncSession = Depends(get_db),
    doc_in: DocumentoIngestRequest,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Genera embedding con Ollama y guarda el documento en pgvector."""
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
        raise HTTPException(status_code=500, detail=f"Error al ingestar documento: {exc}")


@router.post(
    "/rag/ingest-nota/{cita_id}",
    status_code=201,
    summary="Ingestar una nota médica existente al almacén vectorial",
)
async def ingest_nota_medica(
    *,
    db: AsyncSession = Depends(get_db),
    cita_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Busca la nota médica de una cita y la indexa vectorialmente."""
    result = await db.execute(
        text(
            "SELECT id, diagnostico, tratamiento, observaciones "
            "FROM notas_medicas WHERE cita_id = :cita_id"
        ),
        {"cita_id": cita_id},
    )
    nota = result.mappings().first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota médica no encontrada.")

    contenido_parts = [f"Diagnóstico: {nota['diagnostico']}"]
    if nota["tratamiento"]:
        contenido_parts.append(f"Tratamiento: {nota['tratamiento']}")
    if nota["observaciones"]:
        contenido_parts.append(f"Observaciones: {nota['observaciones']}")
    contenido = "\n".join(contenido_parts)

    doc_result = await ingest_documento(
        db,
        ref_tipo="NOTA_MEDICA",
        ref_id=nota["id"],
        titulo=f"Nota médica cita #{cita_id}",
        contenido=contenido,
    )
    return doc_result


@router.post(
    "/rag/search",
    response_model=list[DocumentoSearchResult],
    summary="Buscar documentos por similitud semántica",
)
async def search(
    *,
    db: AsyncSession = Depends(get_db),
    search_in: DocumentoSearchRequest,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Realiza búsqueda por embedding sobre documentos_vectoriales."""
    try:
        results = await search_documentos(
            db, search_in.query, k=search_in.k, ref_tipo=search_in.ref_tipo
        )
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {exc}")


@router.post(
    "/rag/chat",
    response_model=ChatResponse,
    summary="Conversar con el agente MedAssist (RAG + tool calling)",
)
async def chat(
    *,
    db: AsyncSession = Depends(get_db),
    chat_in: ChatRequest,
    current_user: UserModel = Depends(get_current_user),
) -> ChatResponse:
    """Envía un mensaje al agente que puede consultar la BD y documentos vectoriales."""
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
        raise HTTPException(status_code=500, detail=f"Error del agente: {exc}")
