"""add unique document_number to patients and doctors (idempotente)

Revision ID: add_document_number
Revises: fix_appointments_user_id_type

`script_BD/init.sql` ya declara `document_number VARCHAR(50) NOT NULL UNIQUE`
en `patients` y `doctors`, asi que el `add_column` + `alter_column` +
`create_unique_constraint` originales fallaban con DuplicateColumn /
DuplicateObject en toda base recien creada.

Ademas, hacer NOT NULL una columna recien anadida a una tabla con filas exigiria
un valor por defecto; la migracion original solo podia funcionar sobre tablas
vacias. Por eso, sobre datos existentes se rellena con `LEGACY-PAT-<id>`.

Ahora es idempotente y funciona tanto en base nueva como sembrada.
"""

import sqlalchemy as sa
from alembic import op

revision = "add_document_number"
down_revision = "fix_appointments_user_id_type"
branch_labels = None
depends_on = None

TABLAS = [
    ("patients", "patients_document_number_key", "LEGACY-PAT-"),
    ("doctors", "doctors_document_number_key", "LEGACY-DOC-"),
]


def _tiene_columna(bind, tabla: str, columna: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ).bindparams(t=tabla, c=columna)
        ).scalar()
    )


def _tiene_indice(bind, nombre: str) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"),
            {"n": nombre},
        ).scalar()
    )


def upgrade() -> None:
    bind = op.get_bind()
    for tabla, constraint, prefijo in TABLAS:
        if not _tiene_columna(bind, tabla, "document_number"):
            op.add_column(
                tabla, sa.Column("document_number", sa.String(50), nullable=True)
            )

        # Rellenar antes del NOT NULL: sobre una tabla con filas, anadir la
        # columna como NOT NULL sin default es imposible.
        op.execute(
            f"UPDATE {tabla} SET document_number = '{prefijo}' || id "
            "WHERE document_number IS NULL"
        )

        op.alter_column(
            tabla, "document_number", nullable=False, existing_type=sa.String(50)
        )

        if not _tiene_indice(bind, constraint):
            op.create_unique_constraint(constraint, tabla, ["document_number"])


def downgrade() -> None:
    bind = op.get_bind()
    for tabla, constraint, _ in TABLAS:
        if _tiene_indice(bind, constraint):
            op.drop_constraint(constraint, tabla, type_="unique")
        if _tiene_columna(bind, tabla, "document_number"):
            op.drop_column(tabla, "document_number")