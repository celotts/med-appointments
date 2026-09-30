"""Refresh tokens: lo que hace que cerrar sesion cierre de verdad.

## Por que no es un JWT

Un refresh token firmado (JWT) se puede verificar sin tocar la base, pero no se
puede revocar: seguiria valiendo hasta que expire. Eso obliga a mantener una
lista de bloqueo, que es la tabla que se queria evitar.

Un token opaco —una cadena aleatoria de 32 bytes— no se puede falsificar (no
lleva la firma) y se guarda **hasheado** en la base. Cerrar sesion es borrar la
fila, y el token deja de servir en el acto.

Guardar el hash y no el token importa: si alguien lee la tabla (un dump, una
inyeccion SQL) obtiene hashes, no tokens usables. Es el mismo motivo por el que
las contrasenas se guardan hasheadas.

Ver `docs/SEGURIDAD.md`.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, String, func, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RefreshToken(Base):
    """Un refresh token activo. Su ausencia significa "sesion cerrada"."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # SHA-256 del token, nunca el token en si mismo.
    hashed_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # De donde viene la sesion: "web", "movil"...
    # Permite despues mostrar "sesiones activas" y cerrar una concreta.
    origen: Mapped[str] = mapped_column(String(32), nullable=False, default="web")
    # IP del ultimo uso. Un refresh desde otra IP es una senal de robo.
    last_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def esta_vigente(self) -> bool:
        return (
            self.revoked_at is None
            and self.expires_at > datetime.now(timezone.utc)
        )

    def __repr__(self) -> str:
        return (
            f"RefreshToken(user_id={self.user_id}, "
            f"vigente={self.esta_vigente()})"
        )


def generar_token() -> str:
    """Token opaco de 32 bytes, en URL-safe base64.

    `secrets.token_urlsafe` usa el generador criptografico del sistema. NO se
    usa `random`: es predecible y un atacante podria adivinar el token de otro.
    """
    return secrets.token_urlsafe(32)


def hashear_token(token: str) -> str:
    """SHA-256 en hexadecimal. El token nunca se guarda en claro."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def caducidad(dias: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=dias)
