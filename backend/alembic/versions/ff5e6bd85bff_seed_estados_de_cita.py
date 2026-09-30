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
    # NOTA: esta migracion crea `COMPLETADA` en lugar de `ATENDIDA`. No se
    # corrige aqui a proposito: las migraciones ya aplicadas no se reescriben.
    # La correccion vive en c9d2a1e6f304_normaliza_estados_cita, que remapea
    # COMPLETADA -> ATENDIDA e inserta los 8 estados canonicos.
    bind = op.get_bind()
    for estado in [
        {"code": "PENDIENTE", "description": "Cita pendiente de confirmación"},
        {"code": "CONFIRMADA", "description": "Cita confirmada"},
        {"code": "COMPLETADA", "description": "Cita completada"},
        {"code": "CANCELADA", "description": "Cita cancelada"},
        {"code": "SUSPENDIDA", "description": "Cita suspendida"},
        {"code": "REAGENDADA", "description": "Cita reagendada a nueva fecha"},
    ]:
        # Idempotente: script_BD/seeds/seed_catalogs.sql puede haber corrido antes.
        bind.execute(
            sa.text(
                "INSERT INTO appointment_statuses (code, description) "
                "VALUES (:code, :description) ON CONFLICT (code) DO NOTHING"
            ).bindparams(**estado)
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM appointment_statuses WHERE code IN "
        "('PENDIENTE','CONFIRMADA','COMPLETADA','CANCELADA','SUSPENDIDA','REAGENDADA')"
    )
