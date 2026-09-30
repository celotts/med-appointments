"""Add user_id column to appointments table (idempotente)

Revision ID: 20260913_01
Revises: add_is_specialist_to_users

CORRECCION 2026-09-30
---------------------
`script_BD/init.sql` ya declara `appointments.user_id UUID`, asi que el
`op.add_column` original fallaba con DuplicateColumnError en toda base
recien creada, rompiendo el flujo init.sql + `alembic upgrade head`.

Se usa `ADD COLUMN IF NOT EXISTS` y se conserva el tipo UUID del esquema
(originalmente esta migracion lo creaba como Integer, y la siguiente lo
corregia a UUID).
"""

import sqlalchemy as sa
from alembic import op

revision = '20260913_01'
down_revision = 'add_is_specialist_to_users'
branch_labels = None
depends_on = None


def upgrade():
    """Add user_id column to appointments (UUID, nullable)."""
    op.execute(
        "ALTER TABLE appointments "
        "ADD COLUMN IF NOT EXISTS user_id UUID NULL"
    )


def downgrade():
    op.execute("ALTER TABLE appointments DROP COLUMN IF EXISTS user_id")