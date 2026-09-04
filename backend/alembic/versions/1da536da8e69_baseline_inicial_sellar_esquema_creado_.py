"""baseline inicial: sellar esquema creado por init.sql

Revision ID: 1da536da8e69
Revises: 
Create Date: 2026-09-03 19:59:10.975086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1da536da8e69'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
