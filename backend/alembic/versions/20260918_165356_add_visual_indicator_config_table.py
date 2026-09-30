"""add visual_indicator_config table (idempotente)

Revision ID: add_visual_indicator_config
Revises:
Create Date: 2024-01-15

CORRECCION 2026-09-30
---------------------
Esta migracion fallaba en cualquier base recien creada: `script_BD/init.sql`
ya crea la tabla `visual_indicator_config`, y aqui se volvia a crear con
`op.create_table`, produciendo:

    sqlalchemy.exc.ProgrammingError: (psycopg.errors.DuplicateTable)
    relation "visual_indicator_config" already exists

Es decir, el flujo documentado (init.sql + `alembic upgrade head`) estaba roto:
`make test-back` y `ci.yml` ejecutan exactamente esa secuencia.

Ahora la migracion es idempotente: comprueba la existencia de la tabla y del
indice antes de crearlos, y usa `ON CONFLICT DO NOTHING` para la semilla.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_visual_indicator_config'
down_revision = None
branch_labels = None
depends_on = None

INDICE = 'ix_visual_indicator_config_code'

SEMILLA = [
    {'code': 'proximity_rank_1', 'label': 'Próxima cita (1er puesto)', 'hex_color': '#10B981', 'sort_order': 1, 'is_active': True},
    {'code': 'proximity_rank_2', 'label': 'Próxima cita (2do puesto)', 'hex_color': '#3B82F6', 'sort_order': 2, 'is_active': True},
    {'code': 'proximity_rank_3', 'label': 'Próxima cita (3er puesto)', 'hex_color': '#F59E0B', 'sort_order': 3, 'is_active': True},
    {'code': 'delayed', 'label': 'Demorada', 'hex_color': '#EF4444', 'sort_order': 0, 'is_active': True},
    {'code': 'pending', 'label': 'Pendiente', 'hex_color': '#6B7280', 'sort_order': 10, 'is_active': True},
    {'code': 'confirmed', 'label': 'Confirmada', 'hex_color': '#3B82F6', 'sort_order': 5, 'is_active': True},
    {'code': 'completed', 'label': 'Completada', 'hex_color': '#10B981', 'sort_order': 20, 'is_active': True},
    {'code': 'cancelled', 'label': 'Cancelada', 'hex_color': '#EF4444', 'sort_order': 30, 'is_active': True},
    {'code': 'rescheduled', 'label': 'Reagendada', 'hex_color': '#F59E0B', 'sort_order': 15, 'is_active': True},
]


def _existe(bind, sql: str) -> bool:
    return bool(bind.execute(sa.text(sql)).scalar())


def upgrade() -> None:
    bind = op.get_bind()

    # --- Tabla ---
    if not _existe(bind, "SELECT to_regclass('public.visual_indicator_config')"):
        op.create_table(
            'visual_indicator_config',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(50), nullable=False),
            sa.Column('label', sa.String(100), nullable=False),
            sa.Column('hex_color', sa.String(7), nullable=False, server_default='#6B7280'),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code')
        )

    # --- Indice ---
    if not _existe(
        bind,
        "SELECT 1 FROM pg_indexes "
        "WHERE tablename = 'visual_indicator_config' AND indexname = 'ix_visual_indicator_config_code'",
    ):
        op.create_index(
            INDICE, 'visual_indicator_config', ['code'], unique=True
        )

    # --- Semilla ---
    # init.sql ya inserta estas filas; ON CONFLICT DO NOTHING evita duplicados.
    for fila in SEMILLA:
        bind.execute(
            sa.text(
                "INSERT INTO visual_indicator_config "
                "(code, label, hex_color, sort_order, is_active) "
                "VALUES (:code, :label, :hex_color, :sort_order, :is_active) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(**fila)
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _existe(bind, "SELECT to_regclass('public.visual_indicator_config')"):
        op.drop_table('visual_indicator_config')