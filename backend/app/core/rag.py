"""RAG core: embeddings and vector search over vector_documents."""

from typing import Any

import asyncpg
from core.config import settings
from langchain_ollama import OllamaEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

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
    """Converts the SQLAlchemy DSN to asyncpg format."""
    url = settings.DATABASE_URL
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(_get_dsn())


async def ingest_document(
    db: AsyncSession,
    *,
    reference_type: str,
    reference_id: int | None,
    title: str,
    content: str,
) -> dict[str, Any]:
    """Generates embedding and saves the document in vector_documents."""
    embeddings = _get_embeddings()
    vector = embeddings.embed_query(content)
    vector_literal = _vector_str(vector)

    conn = await _connect()
    try:
        await conn.execute(
            "INSERT INTO vector_documents (reference_type, reference_id, title, content, embedding) "
            "VALUES ($1, $2, $3, $4, $5::vector)",
            reference_type,
            reference_id,
            title,
            content,
            vector_literal,
        )
    finally:
        await conn.close()

    return {
        "reference_type": reference_type,
        "reference_id": reference_id,
        "title": title,
    }


async def search_documents(
    db: AsyncSession,
    query: str,
    *,
    k: int = 5,
    reference_type: str | None = None,
) -> list[dict[str, Any]]:
    """Searches documents by cosine similarity in vector_documents."""
    embeddings = _get_embeddings()
    query_vector = embeddings.embed_query(query)
    qv_literal = _vector_str(query_vector)

    conn = await _connect()
    try:
        if reference_type:
            rows = await conn.fetch(
                "SELECT id, reference_type, reference_id, title, content, "
                "1 - (embedding <=> $1::vector) AS similarity "
                "FROM vector_documents WHERE reference_type = $2 "
                "ORDER BY embedding <=> $1::vector LIMIT $3",
                qv_literal,
                reference_type,
                k,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, reference_type, reference_id, title, content, "
                "1 - (embedding <=> $1::vector) AS similarity "
                "FROM vector_documents "
                "ORDER BY embedding <=> $1::vector LIMIT $2",
                qv_literal,
                k,
            )
    finally:
        await conn.close()

    return [
        {
            "id": r["id"],
            "reference_type": r["reference_type"],
            "reference_id": r["reference_id"],
            "title": r["title"],
            "content": r["content"][:500],
            "similarity": round(float(r["similarity"]), 4),
        }
        for r in rows
    ]


async def search_appointments_by_text(
    db: AsyncSession,
    query: str,
    *,
    k: int = 3,
) -> list[dict[str, Any]]:
    """Searches in medical notes using embedding."""
    embeddings = _get_embeddings()
    query_vector = embeddings.embed_query(query)
    qv_literal = _vector_str(query_vector)

    conn = await _connect()
    try:
        rows = await conn.fetch(
            "SELECT nm.id, nm.appointment_id, nm.diagnosis, nm.treatment, nm.observations, "
            "1 - (dv.embedding <=> $1::vector) AS similarity "
            "FROM medical_notes nm "
            "JOIN vector_documents dv ON dv.reference_type = 'MEDICAL_NOTE' AND dv.reference_id = nm.id "
            "ORDER BY dv.embedding <=> $1::vector LIMIT $2",
            qv_literal,
            k,
        )
    finally:
        await conn.close()

    return [
        {
            "note_id": r["id"],
            "appointment_id": r["appointment_id"],
            "diagnosis": r["diagnosis"],
            "treatment": r["treatment"],
            "observations": r["observations"],
            "similarity": round(float(r["similarity"]), 4),
        }
        for r in rows
    ]
