"""Add is_specialist column to users table (idempotente)

Revision ID: add_is_specialist_to_users
Revises: ff5e6bd85bff
Revision Notes: Columna is_specialist para la agenda de especialistas.

CORRECCION 2026-09-30
---------------------
`script_BD/init.sql` ya declara `users.is_specialist`, asi que el
`op.add_column` original fallaba en toda base recien creada:

    asyncpg.exceptions.DuplicateColumnError:
    column "is_specialist" of relation "users" already exists

Rompia el flujo documentado (init.sql + `alembic upgrade head`), que es
exactamente lo que ejecutan `make test-back` y `ci.yml`.

Ahora se comprueba la columna antes de anadirla.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_is_specialist_to_users'
down_revision = 'ff5e6bd85bff'
branch_labels = None
depends_on = None


def _tiene_columna(bind, tabla: str, columna: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :tabla AND column_name = :columna"
            ).bindparams(tabla=tabla, columna=columna)
        ).scalar()
    )


def upgrade():
    """Add is_specialist column to users table."""
    bind = op.get_bind()
    if not _tiene_columna(bind, 'users', 'is_specialist'):
        op.add_column(
            'users',
            sa.Column(
                'is_specialist',
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            ),
        )


def downgrade():
    """Remove is_specialist column from users table."""
    bind = op.get_bind()
    if _tiene_columna(bind, 'users', 'is_specialist'):
        op.drop_column('users', 'is_specialist')