"""Add is_specialist column to users table

Revision ID: 20240101_01
Revision Notes: Add is_specialist column to users table for specialist agenda feature

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_is_specialist_to_users'
down_revision = 'ff5e6bd85bff'
branch_labels = None
depends_on = None


def upgrade():
    """Add is_specialist column to users table."""
    op.add_column('users', sa.Column('is_specialist', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    """Remove is_specialist column from users table."""
    op.drop_column('users', 'is_specialist')
