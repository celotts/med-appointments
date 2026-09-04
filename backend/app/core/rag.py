"""Core de RAG: embeddings y búsqueda vectorial sobre documentos_vectoriales."""

from typing import Any

import asyncpg
from langchain_ollama import OllamaEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

_EMBEDDINGS_INSTANCE: OllamaEmbeddings | None = None


def _get_embeddings() -> OllamaEmbeddings:
    global _EMBEDDINGS_INSTANCE
    if _EMBEDDINGS_INSTANCE is None:
        _EMBEDDINGS_INSTANCE = OllamaEmbeddings(
            model=settings.OLLAMA_EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )
    return _EMBEDDINGS_INSTANCE


def _vector_str(vector: list[float]) -> str:
    return "[" + ",".join(str(v) for v in vector) + "]"


def _get_dsn() -> str:
    """Convierte el DSN de SQLAlchemy al formato asyncpg."""
    url = settings.DATABASE_URL
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(_get_dsn())


async def ingest_documento(
    db: AsyncSession,
    *,
    ref_tipo: str,
    ref_id: int | None,
    titulo: str,
    contenido: str,
) -> dict[str, Any]:
    """Genera embedding y guarda el documento en documentos_vectoriales."""
    embeddings = _get_embeddings()
    vector = embeddings.embed_query(contenido)
    vector_literal = _vector_str(vector)

    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO documentos_vectoriales (ref_tipo, ref_id, titulo, contenido, embedding) "
            "VALUES ($1, $2, $3, $4, $5::vector)",
            ref_tipo,
            ref_id,
            titulo,
            contenido,
            vector_literal,
        )
    finally:
        await conn.close()

    return {
        "ref_tipo": ref_tipo,
        "ref_id": ref_id,
        "titulo": titulo,
    }


async def search_documentos(
    db: AsyncSession,
    query: str,
    *,
    k: int = 5,
    ref_tipo: str | None = None,
) -> list[dict[str, Any]]:
    """Busca documentos por similitud coseno en documentos_vectoriales."""
    embeddings = _get_embeddings()
    query_vector = embeddings.embed_query(query)
    qv_literal = _vector_str(query_vector)

    conn = await _connect()
    try:
        if ref_tipo:
            rows = await conn.fetch(
                "SELECT id, ref_tipo, ref_id, titulo, contenido, "
                "1 - (embedding <=> $1::vector) AS similarity "
                "FROM documentos_vectoriales WHERE ref_tipo = $2 "
                "ORDER BY embedding <=> $1::vector LIMIT $3",
                qv_literal,
                ref_tipo,
                k,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, ref_tipo, ref_id, titulo, contenido, "
                "1 - (embedding <=> $1::vector) AS similarity "
                "FROM documentos_vectoriales "
                "ORDER BY embedding <=> $1::vector LIMIT $2",
                qv_literal,
                k,
            )
    finally:
        await conn.close()

    return [
        {
            "id": r["id"],
            "ref_tipo": r["ref_tipo"],
            "ref_id": r["ref_id"],
            "titulo": r["titulo"],
            "contenido": r["contenido"][:500],
            "similarity": round(float(r["similarity"]), 4),
        }
        for r in rows
    ]


async def search_citas_por_texto(
    db: AsyncSession,
    query: str,
    *,
    k: int = 3,
) -> list[dict[str, Any]]:
    """Busca en notas médicas usando embedding."""
    embeddings = _get_embeddings()
    query_vector = embeddings.embed_query(query)
    qv_literal = _vector_str(query_vector)

    conn = await _connect()
    try:
        rows = await conn.fetch(
            "SELECT nm.id, nm.cita_id, nm.diagnostico, nm.tratamiento, nm.observaciones, "
            "1 - (dv.embedding <=> $1::vector) AS similarity "
            "FROM notas_medicas nm "
            "JOIN documentos_vectoriales dv ON dv.ref_tipo = 'NOTA_MEDICA' AND dv.ref_id = nm.id "
            "ORDER BY dv.embedding <=> $1::vector LIMIT $2",
            qv_literal,
            k,
        )
    finally:
        await conn.close()

    return [
        {
            "nota_id": r["id"],
            "cita_id": r["cita_id"],
            "diagnostico": r["diagnostico"],
            "tratamiento": r["tratamiento"],
            "observaciones": r["observaciones"],
            "similarity": round(float(r["similarity"]), 4),
        }
        for r in rows
    ]
