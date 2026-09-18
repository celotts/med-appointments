"""add unique document_number to patients and doctors

Revision ID: add_document_number
Revises: fix_appointments_user_id_type
Create Date: 2026-09-18

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "add_document_number"
down_revision: str | None = "fix_appointments_user_id_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "patients", sa.Column("document_number", sa.String(50), nullable=True)
    )
    op.execute(
        "UPDATE patients SET document_number = 'LEGACY-PAT-' || id "
        "WHERE document_number IS NULL"
    )
    op.alter_column("patients", "document_number", nullable=False)
    op.create_unique_constraint(
        "patients_document_number_key", "patients", ["document_number"]
    )

    op.add_column(
        "doctors", sa.Column("document_number", sa.String(50), nullable=True)
    )
    op.execute(
        "UPDATE doctors SET document_number = 'LEGACY-DOC-' || id "
        "WHERE document_number IS NULL"
    )
    op.alter_column("doctors", "document_number", nullable=False)
    op.create_unique_constraint(
        "doctors_document_number_key", "doctors", ["document_number"]
    )


def downgrade() -> None:
    op.drop_constraint("doctors_document_number_key", "doctors", type_="unique")
    op.drop_column("doctors", "document_number")
    op.drop_constraint("patients_document_number_key", "patients", type_="unique")
    op.drop_column("patients", "document_number")
