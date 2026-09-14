"""Fix user_id column type in appointments table

Revision ID: fix_appointments_user_id_type
Revision Notes: Change user_id from INTEGER to UUID in appointments table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_appointments_user_id_type'
down_revision = '20260913_01'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('appointments', 'user_id',
                    type=sa.Uuid(),
                    existing_type=sa.Integer(),
                    postgresql_using="appointments.user_id::uuid")


def downgrade():
    op.alter_column('appointments', 'user_id',
                    type=sa.Integer(),
                    existing_type=sa.Uuid(),
                    postgresql_using="appointments.user_id::integer")
