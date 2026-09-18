from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from modules.appointments import crud
from modules.appointments.schemas import AppointmentCreate, AppointmentUpdate

from ..db import session_factory


def _as_dict(appointment: Any) -> dict[str, Any]:
    return {
        "id": appointment.id,
        "patient_id": appointment.patient_id,
        "doctor_id": appointment.doctor_id,
        "status_id": appointment.status_id,
        "start_datetime": appointment.start_datetime.isoformat()
        if appointment.start_datetime
        else None,
        "end_datetime": appointment.end_datetime.isoformat() if appointment.end_datetime else None,
        "reason": appointment.reason,
        "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
    }


async def appointment_list(skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
    """Lista citas médicas. skip: cuántas omitir, limit: cuántas devolver (máx. 100)."""
    async with session_factory() as db:
        rows = await crud.get_appointments(db, skip=skip, limit=limit)
        return [_as_dict(row) for row in rows]


async def appointment_get(appointment_id: int) -> dict[str, Any]:
    """Obtiene una cita por su id."""
    async with session_factory() as db:
        row = await crud.get_appointment(db, appointment_id)
        if row is None:
            return {"error": "Appointment not found"}
        return _as_dict(row)


async def appointment_create(
    patient_id: int,
    doctor_id: int,
    status_id: int,
    start_datetime: str,
    end_datetime: str,
    reason: str,
) -> dict[str, Any]:
    """Crea una nueva cita. Las fechas en formato ISO 8601, ej. '2026-09-20T10:00:00'."""
    payload = AppointmentCreate(
        patient_id=patient_id,
        doctor_id=doctor_id,
        status_id=status_id,
        start_datetime=datetime.fromisoformat(start_datetime),
        end_datetime=datetime.fromisoformat(end_datetime),
        reason=reason,
    )
    async with session_factory() as db:
        row = await crud.create_appointment(db, payload)
        return _as_dict(row)


async def appointment_update(
    appointment_id: int,
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    status_id: Optional[int] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """Actualiza campos de una cita existente. Solo se cambia lo indicado; ignora nulos."""
    calls: dict[str, Any] = {}
    if patient_id is not None:
        calls["patient_id"] = patient_id
    if doctor_id is not None:
        calls["doctor_id"] = doctor_id
    if status_id is not None:
        calls["status_id"] = status_id
    if start_datetime is not None:
        calls["start_datetime"] = datetime.fromisoformat(start_datetime)
    if end_datetime is not None:
        calls["end_datetime"] = datetime.fromisoformat(end_datetime)
    if reason is not None:
        calls["reason"] = reason
    update = AppointmentUpdate(**calls)
    async with session_factory() as db:
        row = await crud.update_appointment(db, appointment_id, update)
        if row is None:
            return {"error": "Appointment not found"}
        return _as_dict(row)


async def appointment_delete(appointment_id: int) -> dict[str, Any]:
    """Elimina una cita. Uso bajo demanda: no incluida por defecto en config.json."""
    async with session_factory() as db:
        deleted = await crud.delete_appointment(db, appointment_id)
        return {"deleted": deleted, "appointment_id": appointment_id}


TOOLS: dict[str, object] = {
    "appointment_list": appointment_list,
    "appointment_get": appointment_get,
    "appointment_create": appointment_create,
    "appointment_update": appointment_update,
    "appointment_delete": appointment_delete,
}