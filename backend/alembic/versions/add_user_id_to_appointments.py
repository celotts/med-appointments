"""Add user_id column to appointments table

Revision ID: 20260913_01
Revision Notes: Add user_id column to appointments table for data isolation by user
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260913_01'
down_revision = 'add_is_specialist_to_users'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('appointments', sa.Column('user_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('appointments', 'user_id')
