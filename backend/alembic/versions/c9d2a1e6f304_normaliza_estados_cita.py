"""normaliza estados de cita al vocabulario canonico

Este proyecto sufria de TRES vocabularios de estados de cita distintos:

  1. Enum de la app (schemas/appointment.py): PENDIENTE, CONFIRMADA,
     EN ESPERA, EN PROCESO, ATENDIDA, CANCELADA, SUSPENDIDA, REAGENDADA
  2. Migracion ff5e6bd85bff: usaba COMPLETADA (ATENDIDA no existia)
  3. seed_large_dataset.py: usaba codigos en ingles (SCHEDULED, CONFIRMED,
     COMPLETED, CANCELLED, ...) que el enum nunca reconocio

Consecuencia: sobre una base limpia, EN ESPERA / EN PROCESO / ATENDIDA no
existian, por lo que /appointments/{id}/wait, /start y /attend fallaban, y
las citas creadas por el seed de Docker tenian codigos que hacian fallar
AppointmentStatusCode(...).

Esta migracion:
  1. Remapea las citas existentes a los codigos canonicos.
  2. Inserta los 8 estados canonicos (idempotente).
  3. Elimina los estados no canonicos que ya no tengan citas.

Es idempotente y segura de ejecutar mas de una vez.

Revision ID: c9d2a1e6f304
Revises: b1f4c7e92a00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d2a1e6f304"
down_revision: str | None = "b1f4c7e92a00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Vocabulario canonico. Fuente de verdad: backend/app/schemas/appointment.py
# (enum AppointmentStatusCode). NO cambiar esta lista sin actualizar antes
# schemas/appointment.py y el frontend.
ESTADOS_CANONICOS = [
    ("PENDIENTE", "Cita pendiente de confirmacion"),
    ("CONFIRMADA", "Cita confirmada"),
    ("EN ESPERA", "Cita en sala de espera"),
    ("EN PROCESO", "Consulta en curso"),
    ("ATENDIDA", "Cita atendida"),
    ("CANCELADA", "Cita cancelada"),
    ("SUSPENDIDA", "Cita suspendida"),
    ("REAGENDADA", "Cita reagendada a nueva fecha"),
]

# Codigos historicos -> canonico.
# Los codigos en ingles provenian de seed_large_dataset.py.
REMAPEO = {
    "COMPLETADA": "ATENDIDA",
    "SCHEDULED": "PENDIENTE",
    "PENDING": "PENDIENTE",
    "CONTACTED": "PENDIENTE",
    "REFERRED": "CANCELADA",
    "EMERGENCY": "PENDIENTE",
    "CONFIRMED": "CONFIRMADA",
    "WAITING": "EN ESPERA",
    "IN_PROGRESS": "EN PROCESO",
    "COMPLETED": "ATENDIDA",
    "ATTENDED": "ATENDIDA",
    "CANCELLED": "CANCELADA",
    "NO_SHOW": "CANCELADA",
    "NOSHOW": "CANCELADA",
    "RESCHEDULED": "REAGENDADA",
    "SUSPENDED": "SUSPENDIDA",
}


def upgrade() -> None:
    bind = op.get_bind()

    # --- Paso 0: restaurar los estados canonicos para poder apuntar a ellos ---
    for code, desc in ESTADOS_CANONICOS:
        bind.execute(
            sa.text(
                "INSERT INTO appointment_statuses (code, description) "
                "VALUES (:code, :desc) ON CONFLICT (code) DO NOTHING"
            ).bindparams(code=code, desc=desc)
        )

    ids = {
        code: ident
        for code, ident in bind.execute(
            sa.text("SELECT code, id FROM appointment_statuses")
        ).fetchall()
    }

    # --- Paso 1: remapear citas existentes ---
    for viejo, nuevo in REMAPEO.items():
        if viejo not in ids or nuevo not in ids or viejo == nuevo:
            continue
        bind.execute(
            sa.text(
                "UPDATE appointments SET status_id = :nuevo WHERE status_id = :viejo"
            ).bindparams(nuevo=ids[nuevo], viejo=ids[viejo])
        )

    # --- Paso 2: normalizar el texto de las descripciones ---
    for code, desc in ESTADOS_CANONICOS:
        bind.execute(
            sa.text(
                "UPDATE appointment_statuses SET description = :desc WHERE code = :code"
            ).bindparams(code=code, desc=desc)
        )

    # --- Paso 3: borrar estados no canonicos que ya no tengan citas ---
    canonicos = {code for code, _ in ESTADOS_CANONICOS}
    for code in list(ids):
        if code in canonicos:
            continue
        # appointments.status_id tiene ON DELETE RESTRICT: no borrar si se usa.
        huerfano = bind.execute(
            sa.text(
                "SELECT NOT EXISTS "
                "(SELECT 1 FROM appointments WHERE status_id = :sid)"
            ).bindparams(sid=ids[code])
        ).scalar()
        if huerfano:
            bind.execute(
                sa.text("DELETE FROM appointment_statuses WHERE id = :sid").bindparams(
                    sid=ids[code]
                )
            )


def downgrade() -> None:
    """No se revierte.

    Revertir exigiria volver a partir las citas entre COMPLETADA y ATENDIDA,
    distincion que ya no es recuperable de forma univoca. Revierte el merge
    de migraciones, no la normalizacion de datos.
    """
