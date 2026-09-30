"""merge doble head

Une las dos ramas de migración que existían (add_document_number y
add_visual_indicator_config) en un único head lineal.

Motivo: ambos archivos declaraban down_revision = None, lo que dejaba DOS
heads y hacía fallar `alembic upgrade head`. Solo `upgrade heads` funcionaba.

Revision ID: b1f4c7e92a00
Revises: add_document_number, add_visual_indicator_config
"""

from collections.abc import Sequence

revision: str = "b1f4c7e92a00"
down_revision: tuple[str, str] = ("add_document_number", "add_visual_indicator_config")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Sin cambios de esquema: solo une el grafo de migraciones."""


def downgrade() -> None:
    """Sin cambios de esquema: solo deshace la unión del grafo."""
