"""Carga por medico y ocupacion de agenda.

Separado de `crud_dashboard_metrics.py` para que ese modulo no pase de las 250
lineas que fija `TRABAJO_ACUERDO.md`.

## Ocupacion: por que puede ser None

La ocupacion compara los minutos agendados con los minutos que el medico tiene
disponibles, y el denominator sale de `doctor_schedules` (`day_of_week` +
`slot_duration_minutes`). Si un medico no tiene horario cargado, no hay
denominador: se devuelve `None`, no 0.

La diferencia importa: 0% dice "no tiene pacientes", `None` dice "no se puede
saber". Un asistente que ve "0% ocupacion" tomaria una decision equivocada.

Los minutos de cada cita salen de `end_datetime - start_datetime`, que es el
dato real; no se asume una duracion promedio.

Ver `docs/FRONTEND.md`.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.appointment import Appointment as AppointmentModel
from models.appointment_status import AppointmentStatus as StatusModel
from models.doctor import Doctor as DoctorModel
from models.doctor_schedule import DoctorSchedule
from models.specialty import Specialty

from core.crud_dashboard_metrics import OCUPAN_AGENDA


def _dias_de_la_semana_en(desde: datetime, dias: int, dia_semana: int) -> int:
    """Cuantas veces cae `dia_semana` (0=lunes) dentro del periodo.

    `date.weekday()` devuelve 0 para lunes, que es la misma convencion que usa
    `doctor_schedules.day_of_week`.
    """
    return sum(
        1 for offset in range(dias) if (desde + timedelta(days=offset)).weekday() == dia_semana
    )


async def _minutos_disponibles(db: AsyncSession, doctor_id: int, dias: int) -> float | None:
    """Minutos de agenda del medico en el periodo. None si no tiene horario.

    ## El denominador se calcula con start_time y end_time

    Una version anterior sumaba solo `slot_duration_minutes` y ya estaba: con
    un turno de 09:00 a 17:00 en bloques de 30 min daba 150 minutos de
    disponibilidad frente a los 2400 reales, y la ocupacion salia en
    270-304%.

    Un 300% de ocupacion no es un dato extremo: es un calculo roto.

    El tiempo por dia sale de `end_time - start_time`, que es lo que el medico
    declaró. `slot_duration_minutes` solo se usa si el turno viniera sin horas.
    """
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    result = await db.execute(
        select(
            DoctorSchedule.day_of_week,
            DoctorSchedule.start_time,
            DoctorSchedule.end_time,
            DoctorSchedule.slot_duration_minutes,
        ).where(DoctorSchedule.doctor_id == doctor_id)
    )
    horarios = result.all()
    if not horarios:
        return None

    total = 0.0
    for dia_semana, inicio, fin, slot in horarios:
        minutos_dia = _minutos_de_turno(inicio, fin, slot)
        total += _dias_de_la_semana_en(desde, dias, dia_semana) * minutos_dia

    return total if total > 0 else None


def _minutos_de_turno(
    inicio: time | None, fin: time | None, slot: int | None
) -> float:
    """Minutos de agenda de un dia, segun el bloque declarado.

    Un turno que cruza medianoche se trata como el intervalo mas corto entre
    inicio y fin, que es el caso habitual de un turno nocturno.
    """
    if inicio is not None and fin is not None:
        minutos = (fin.hour * 60 + fin.minute) - (inicio.hour * 60 + inicio.minute)
        if minutos < 0:
            minutos += 24 * 60
        if minutos > 0:
            return float(minutos)
    return float(slot or 30)


async def ocupacion_pct(db: AsyncSession, doctor_id: int, dias: int) -> float | None:
    """Porcentaje de ocupacion. None cuando no se puede calcular."""
    disponibles = await _minutos_disponibles(db, doctor_id, dias)
    if not disponibles:
        return None

    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    sub_estados = select(StatusModel.id).where(StatusModel.code.in_(OCUPAN_AGENDA))

    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    func.extract("epoch", AppointmentModel.end_datetime)
                    - func.extract("epoch", AppointmentModel.start_datetime)
                ),
                0,
            )
        ).where(
            AppointmentModel.doctor_id == doctor_id,
            AppointmentModel.start_datetime >= desde,
            AppointmentModel.status_id.in_(sub_estados),
        )
    )
    minutos_cita = float(result.scalar() or 0) / 60
    return round(minutos_cita / disponibles * 100, 1)


async def carga_por_medico(
    db: AsyncSession, *, doctor_ids: set[int] | None, dias: int
) -> list[dict]:
    """Carga por medico: total, atendidas, canceladas y ocupacion."""
    if doctor_ids is not None and not doctor_ids:
        return []

    desde = datetime.now(timezone.utc) - timedelta(days=dias)

    stmt = (
        select(
            DoctorModel.id,
            DoctorModel.first_name,
            DoctorModel.last_name,
            Specialty.name.label("especialidad"),
            StatusModel.code,
            func.count(AppointmentModel.id),
        )
        .join(AppointmentModel, AppointmentModel.doctor_id == DoctorModel.id)
        .join(StatusModel, StatusModel.id == AppointmentModel.status_id)
        .join(Specialty, Specialty.id == DoctorModel.specialty_id)
        .where(AppointmentModel.start_datetime >= desde)
        .group_by(DoctorModel.id, Specialty.name, StatusModel.code)
    )
    if doctor_ids is not None:
        stmt = stmt.where(DoctorModel.id.in_(doctor_ids))

    result = await db.execute(stmt)

    por_medico: dict[int, dict] = {}
    for doctor_id, nombre, apellido, especialidad, codigo, total in result.all():
        fila = por_medico.setdefault(
            doctor_id,
            {
                "doctor_id": doctor_id,
                "nombre": f"{nombre} {apellido}",
                "especialidad": especialidad,
                "total": 0,
                "atendidas": 0,
                "canceladas": 0,
            },
        )
        fila["total"] += total
        if codigo == "ATENDIDA":
            fila["atendidas"] += total
        elif codigo == "CANCELADA":
            fila["canceladas"] += total

    # La ocupacion va en una consulta por medico: depende del horario de cada
    # uno, que no se puede agregar en SQL junto al conteo de citas.
    for fila in por_medico.values():
        fila["ocupacion_pct"] = await ocupacion_pct(db, fila["doctor_id"], dias)

    return sorted(por_medico.values(), key=lambda f: -f["total"])


__all__ = ["carga_por_medico", "ocupacion_pct"]
