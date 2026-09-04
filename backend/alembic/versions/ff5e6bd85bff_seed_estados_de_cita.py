"""seed estados de cita

Revision ID: ff5e6bd85bff
Revises: 1da536da8e69
Create Date: 2026-09-03 20:20:32.037316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ff5e6bd85bff'
down_revision: Union[str, None] = '1da536da8e69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    estados = sa.table(
        "estados_cita",
        sa.column("codigo", sa.String),
        sa.column("descripcion", sa.String),
    )
    op.bulk_insert(
        estados,
        [
            {"codigo": "PENDIENTE", "descripcion": "Cita pendiente de confirmación"},
            {"codigo": "CONFIRMADA", "descripcion": "Cita confirmada"},
            {"codigo": "COMPLETADA", "descripcion": "Cita completada"},
            {"codigo": "CANCELADA", "descripcion": "Cita cancelada"},
            {"codigo": "SUSPENDIDA", "descripcion": "Cita suspendida"},
            {"codigo": "REAGENDADA", "descripcion": "Cita reagendada a nueva fecha"},
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM estados_cita")
