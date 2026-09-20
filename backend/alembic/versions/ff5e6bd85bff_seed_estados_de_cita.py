"""seed estados de cita

Revision ID: ff5e6bd85bff
Revises: 1da536da8e69
Create Date: 2026-09-03 20:20:32.037316

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'ff5e6bd85bff'
down_revision: str | None = "1da536da8e69"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    estados = sa.table(
        "appointment_statuses",
        sa.column("code", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(
        estados,
        [
            {"code": "PENDIENTE", "description": "Cita pendiente de confirmación"},
            {"code": "CONFIRMADA", "description": "Cita confirmada"},
            {"code": "COMPLETADA", "description": "Cita completada"},
            {"code": "CANCELADA", "description": "Cita cancelada"},
            {"code": "SUSPENDIDA", "description": "Cita suspendida"},
            {"code": "REAGENDADA", "description": "Cita reagendada a nueva fecha"},
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM appointment_statuses WHERE code IN ('PENDIENTE','CONFIRMADA','COMPLETADA','CANCELADA','SUSPENDIDA','REAGENDADA')")