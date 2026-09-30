"""normaliza roles al vocabulario canonico

init.sql creaba tres roles: SYSTEM_ROLE, SUPER_ADMIN y ASSISTANT.

Eso rompia el control de acceso por tres motivos:

  1. api/endpoints/assistants.py comparaba contra ("admin", "super_admin")
     en minusculas, asi que nunca coincidia con SUPER_ADMIN: devolvia 403
     siempre, incluso al propio superusuario.
  2. El frontend comparaba contra 'admin' y 'super-admin', de modo que nunca
     reconocia a un administrador y le ocultaba acciones ejecutables.
  3. No existian los roles DOCTOR, SPECIALIST ni PATIENT, necesarios para
     acotar la propiedad de citas y notas.

Esta migracion inserta los seis roles canonicos de core/rbac.py usando los
mismos UUID deterministas que ese modulo.

Es idempotente. NO borra ni renombra roles existentes: hacerlo dejaria
huerfano a los usuarios que los referencian.

Revision ID: d4e1b2f7a915
Revises: c9d2a1e6f304
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e1b2f7a915"
down_revision: str | None = "c9d2a1e6f304"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_USER_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"

# (id, name, description) -- debe coincidir con ROLES_CANONICOS en
# backend/app/core/rbac.py. UUIDs dentro del rango reservado de init.sql.
ROLES = [
    ("00000000-0000-0000-0000-000000000002", "SUPER_ADMIN", "Acceso total al sistema"),
    ("00000000-0000-0000-0000-000000000003", "ADMIN", "Administracion de la clinica"),
    ("00000000-0000-0000-0000-000000000004", "ASSISTANT", "Asistente: agenda y pacientes"),
    ("00000000-0000-0000-0000-000000000005", "DOCTOR", "Medico responsable de sus citas"),
    ("00000000-0000-0000-0000-000000000006", "SPECIALIST", "Medico especialista"),
    ("00000000-0000-0000-0000-000000000007", "PATIENT", "Paciente: solo sus propias citas"),
]


def _columnas_roles(bind) -> set[str]:
    return {
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'roles'"
            )
        ).all()
    }


def upgrade() -> None:
    bind = op.get_bind()
    columnas = _columnas_roles(bind)
    # La tabla `roles` no tiene columna `description` en el esquema original:
    # solo se escribe si existe.
    tiene_description = "description" in columnas

    for role_id, name, description in ROLES:
        # `roles.name` tiene UNIQUE, y `init.sql` ya creo SUPER_ADMIN y ASSISTANT
        # con UUIDs distintos a los de este modulo. Insertar por `id` no
        # basta: hay que comprobar tambien el nombre, porque un ON CONFLICT
        # sobre `id` no captura la violacion de `name` (falla antes de llegar
        # al manejador).
        ya_existe = bind.execute(
            sa.text("SELECT 1 FROM roles WHERE id = CAST(:id AS uuid) OR name = :name"),
            {"id": role_id, "name": name},
        ).scalar()
        if ya_existe:
            continue

        if tiene_description:
            bind.execute(
                sa.text(
                    "INSERT INTO roles (id, name, description, created_by_user_id) "
                    "VALUES (CAST(:id AS uuid), :name, :description, CAST(:user AS uuid))"
                ).bindparams(
                    id=role_id, name=name, description=description, user=SYSTEM_USER_ID
                )
            )
        else:
            # `roles.id` es UUID: el valor debe ir casteado, no como texto.
            bind.execute(
                sa.text(
                    "INSERT INTO roles (id, name, created_by_user_id) "
                    "VALUES (CAST(:id AS uuid), :name, CAST(:user AS uuid))"
                ).bindparams(id=role_id, name=name, user=SYSTEM_USER_ID)
            )


def downgrade() -> None:
    """Solo elimina los roles canonicos que ningun usuario referencia."""
    bind = op.get_bind()
    for role_id, _name, _description in ROLES:
        en_uso = bind.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM users WHERE role_id = CAST(:id AS uuid))"
            ).bindparams(id=role_id)
        ).scalar()
        if not en_uso:
            bind.execute(
                sa.text("DELETE FROM roles WHERE id = CAST(:id AS uuid)"),
                {"id": role_id},
            )
