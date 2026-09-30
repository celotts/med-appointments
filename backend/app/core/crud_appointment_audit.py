"""Auditoria de las transiciones de cita.

Un solo punto de entrada para registrar cambios de estado. Todas las funciones
de transicion de `crud_appointment.py` llaman a `transicionar()`, que:

1. Valida la transicion contra `VALID_TRANSITIONS`.
2. Cambia el estado.
3. Escribe el registro de auditoria **en la misma transaccion**.
4. Hace un unico `commit`.

Que sea un unico commit importa: si el registro y el cambio se confirmaran por
separado, un fallo intermedio dejaria un estado cambiado sin rastro, que es
justo lo que la auditoria debe impedir.

## Trampa de SQLAlchemy async: MissingGreenlet

Toda lectura de atributo ORM ocurre **antes** del `flush`/`commit` de la
auditoria. Despues de un flush, la sesion queda expirada y volver a consultar
`db_appointment.status` o `actor.id` lanza:

    sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
    can't call await_only() here

Por eso cada funcion captura primero `status.code`, `actor.id` y
`appointment.id` en variables locales, y solo despues escribe. No es
defensivo: es obligatorio. Si añades un `transicionar()` nuevo, copia el
patron.

Ver `docs/AUDITORIA.md`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core import crud_audit
from models.appointment import Appointment as AppointmentModel
from models.audit import AuditAction
from models.user import User as UserModel
from schemas.appointment import VALID_TRANSITIONS, AppointmentStatusCode
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def transicionar(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    destino: AppointmentStatusCode,
    *,
    actor: UserModel | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    permitir_igual: bool = False,
) -> AppointmentModel:
    """Cambia el estado de una cita validando contra la maquina de estados.

    Lanza `ValueError` si la transicion no es valida; el endpoint lo convierte
    en 400.
    """
    # --- Captura previa obligatoria (ver nota de MissingGreenlet arriba) ---
    status_origen = db_appointment.status.code
    actor_id = getattr(actor, "id", None)
    appointment_id = db_appointment.id

    if status_origen == destino.value:
        if permitir_igual:
            return db_appointment
        raise ValueError(f"La cita ya esta en estado {destino.value}.")

    permitidos = VALID_TRANSITIONS.get(AppointmentStatusCode(status_origen), set())
    if destino not in permitidos:
        raise ValueError(f"Transicion invalida de {status_origen} a {destino.value}.")

    from core.crud_appointment import get_status_by_code

    status_destino = await get_status_by_code(db, destino)
    if status_destino is None:
        raise ValueError(f"El estado {destino.value} no existe en la base de datos.")

    db_appointment.status_id = status_destino.id

    # Auditoria antes del commit: comparte transaccion con el cambio.
    await crud_audit.registrar_transicion_cita(
        db,
        appointment_id=appointment_id,
        from_state=status_origen,
        to_state=destino.value,
        user_id=actor_id,
        reason=reason,
        metadata=metadata,
    )

    await db.commit()
    await db.refresh(db_appointment)
    return db_appointment


async def registrar_creacion(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    *,
    actor: UserModel | None = None,
) -> None:
    """Audita la creacion de una cita (no hay estado previo)."""
    # Captura previa obligatoria: ver nota de MissingGreenlet.
    appointment_id = db_appointment.id
    estado = db_appointment.status.code
    actor_id = getattr(actor, "id", None)

    await crud_audit.registrar_transicion_cita(
        db,
        appointment_id=appointment_id,
        from_state=None,
        to_state=estado,
        user_id=actor_id,
        reason="Cita creada",
    )


async def registrar_borrado(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    *,
    actor: UserModel | None = None,
) -> None:
    """Audita el borrado fisico de una cita.

    Se escribe antes del DELETE y se confirma con el, para que el rastro
    sobreviva al registro que describe.
    """
    # Captura previa obligatoria: ver nota de MissingGreenlet.
    appointment_id = db_appointment.id
    estado = db_appointment.status.code
    inicio = db_appointment.start_datetime
    doctor_id = db_appointment.doctor_id
    patient_id = db_appointment.patient_id
    actor_id = getattr(actor, "id", None)

    await crud_audit.registrar(
        db,
        action=AuditAction.DELETE,
        table_name=crud_audit.TABLA_CITAS,
        record_id=appointment_id,
        user_id=actor_id,
        old_value={
            "status": estado,
            "start_datetime": inicio.isoformat() if inicio else None,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
        },
        new_value={"deleted_at": datetime.now(timezone.utc).isoformat()},
    )


async def registrar_actualizacion(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    *,
    campos: dict[str, Any],
    valores_previos: dict[str, Any],
    actor: UserModel | None = None,
) -> None:
    """Audita un cambio de datos (no de estado): reagendar, editar motivo..."""
    # Captura previa obligatoria: ver nota de MissingGreenlet.
    appointment_id = db_appointment.id
    actor_id = getattr(actor, "id", None)
    estado_actual = db_appointment.status.code

    await crud_audit.registrar(
        db,
        action=AuditAction.UPDATE,
        table_name=crud_audit.TABLA_CITAS,
        record_id=appointment_id,
        user_id=actor_id,
        old_value=valores_previos,
        new_value={
            "status": estado_actual,
            "campos_modificados": sorted(campos),
            "valores": campos,
        },
        reason="Cita actualizada",
    )
