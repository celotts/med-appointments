"""refresh tokens: sesiones revocables

El access token es un JWT de 15 minutos que viaja en cada peticion. No se puede
revocar sin una lista de bloqueo, asi que se acota su ventana.

El refresh token dura 7 dias, pero se guarda HASHEADO en esta tabla, de modo que
cerrar sesion es borrar la fila y el token deja de servir en el acto. Un JWT de
refresh seguira valiendo hasta expirar aunque el usuario cierre sesion, que es
justo lo que se queria evitar.

El token en claro solo existe en la respuesta del login: la base guarda su
SHA-256. Si alguien lee la tabla (un dump, una inyeccion SQL) obtiene hashes,
no tokens usables.

Revision ID: f6b2c3d4e5a7
Revises: d4e1b2f7a915
Create Date: 2026-09-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6b2c3d4e5a7"
down_revision: str | None = "d4e1b2f7a915"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        # SHA-256 en hexadecimal: 64 caracteres.
        sa.Column("hashed_token", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("origen", sa.String(length=32), nullable=False, server_default="web"),
        sa.Column("last_ip", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )

    # `hashed_token` es UNIQUE: la busqueda por hash es el camino caliente de
    # cada refresh, asi que necesita indice propio.
    op.create_index(
        "ix_refresh_tokens_hashed_token", "refresh_tokens", ["hashed_token"], unique=True
    )
    # Para el limite de sesiones por usuario y para "mis sesiones activas".
    op.create_index(
        "ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_hashed_token", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
