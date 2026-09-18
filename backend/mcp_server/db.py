from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.db import async_session_factory as _api_session_factory

_factory: async_sessionmaker[AsyncSession] | None = None


def session_factory(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    """
    Devuelve la fábrica de sesiones del servidor MCP.

    Si no se indica database_url, reutiliza la del proyecto (core.db / .env),
    con lo que el MCP server usa exactamente la misma base de datos que la API.
    """
    global _factory

    if _factory is None:
        if database_url:
            engine = create_async_engine(database_url, echo=False)
            _factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        else:
            _factory = _api_session_factory
    return _factory