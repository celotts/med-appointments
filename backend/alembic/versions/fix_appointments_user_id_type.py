"""Fix user_id column type in appointments (idempotente)

Revision ID: fix_appointments_user_id_type
Revises: 20260913_01

`appointments.user_id` debe ser UUID para referenciar `users.id`. Esta
migracionoriginally la convertia de Integer a UUID.

Con la correccion de 20260913_01 la columna ya nace UUID desde init.sql, asi
que aqui solo se normaliza el tipo siTodavia no lo es. Sobre una base nueva
la sentencia no tiene efecto.
"""

import sqlalchemy as sa
from alembic import op

revision = 'fix_appointments_user_id_type'
down_revision = '20260913_01'
branch_labels = None
depends_on = None


def _tipo_actual(bind) -> str:
    return (
        bind.execute(
            sa.text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'appointments' AND column_name = 'user_id'"
            )
        ).scalar()
        or ''
    )


def upgrade():
    """Convierte user_id a UUID si aun no lo es."""
    bind = op.get_bind()
    if not bind.execute(
        sa.text("SELECT to_regclass('public.appointments')")
    ).scalar():
        return
    if _tipo_actual(bind) == 'uuid':
        return
    op.alter_column(
        'appointments',
        'user_id',
        type=sa.Uuid(),
        existing_type=sa.Integer(),
        postgresql_using="appointments.user_id::uuid",
    )


def downgrade():
    """No se revierte: degradar UUID a Integer perderia informacion."""