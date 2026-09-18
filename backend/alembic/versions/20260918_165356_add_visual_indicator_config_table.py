"""add visual_indicator_config table

Revision ID: add_visual_indicator_config
Revises: 
Create Date: 2024-01-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_visual_indicator_config'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.create_index('ix_visual_indicator_config_code', 'visual_indicator_config', ['code'], unique=True)

    # Seed data
    op.bulk_insert(
        sa.table(
            'visual_indicator_config',
            sa.Column('code', sa.String(50)),
            sa.Column('label', sa.String(100)),
            sa.Column('hex_color', sa.String(7)),
            sa.Column('sort_order', sa.Integer()),
            sa.Column('is_active', sa.Boolean()),
        ),
        [
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
    )


def downgrade() -> None:
    op.drop_index('ix_visual_indicator_config_code', table_name='visual_indicator_config')
    op.drop_table('visual_indicator_config')
