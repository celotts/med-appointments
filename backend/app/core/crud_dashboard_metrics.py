"""Metricas del dashboard operativo.

Cada funcion devuelve datos agregados, nunca entidades. Los estados usan los
8 codigos canonicos (`schemas.appointment.AppointmentStatusCode`); no se
aceptan los codigos en ingles que usa el SQL antiguo de `reports.py`.

## Definiciones que conviene no reinventar

**Inasistencia (no-show).** No es "no hay nota medica": es una cita cuya hora
ya paso, que sigue en un estado que ocupa agenda (`PENDIENTE`, `CONFIRMADA`,
`REAGENDADA`) y que no tiene nota medica. Es la misma definicion que aplica
`crud_appointment.auto_cancel_no_show_appointments` (`crud_appointment.py:705-723`),
para que el dashboard y el job no se contradigan.

**Tasa de asistencia.** `ATENDIDA / (ATENDIDA + CANCELADA + no-show)`. El
denominador excluye lo que aun no ha ocurrido: contar una cita de la manana
como inasistencia a las 8am da un numero que sube solo con el paso del tiempo.

**Ocupacion.** Minutos reservados sobre minutos disponibles segun
`doctor_schedules` (`slot_duration_minutes`, `start_time`, `end_time`). Si un
medico no tiene horario configurado se devuelve `None`, no cero: cero
significaria que no tiene pacientes.

Ver `docs/FRONTEND.md`.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.appointment import Appointment as AppointmentModel
from models.appointment_status import AppointmentStatus as StatusModel
from models.doctor import Doctor as DoctorModel
from models.doctor_schedule import DoctorSchedule
from models.medical_note import MedicalNote
from models.specialty import Specialty

# Estados que ocupan agenda: la cita esta viva y espera su turno.
OCUPAN_AGENDA = ("PENDIENTE", "CONFIRMADA", "REAGENDADA")
# Estados con los que una cita ya no va a ocurrir.
TERMINALES = ("ATENDIDA", "CANCELADA")


def inicio_del_dia(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _subquery_estados(codigos: tuple[str, ...]):
    """Subconsulta con los ids de los estados indicados.

    No es async a proposito: `in_()` solo necesita el objeto SELECT, no
    ejecutarlo. Declararla async obligaba a recordar el `await` en cada uso y
    sin el se pasaba una corrutina al SQL, que revienta con un ArgumentError
    dificil de leer.
    """
    return select(StatusModel.id).where(StatusModel.code.in_(codigos))


async def contar_por_estado(
    db: AsyncSession,
    *,
    doctor_ids: set[int] | None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> dict[str, int]:
    """Citas agrupadas por codigo de estado, dentro de un rango.

    `doctor_ids` None = toda la clinica. Un conjunto vacio devuelve {} sin
    tocar la base de datos, que es lo que hace que un asistente sin
    asignaciones vea un panel vacio en vez de las citas de otro.
    """
    if doctor_ids is not None and not doctor_ids:
        return {}

    stmt = (
        select(StatusModel.code, func.count(AppointmentModel.id))
        .join(StatusModel, StatusModel.id == AppointmentModel.status_id)
    )
    if doctor_ids is not None:
        stmt = stmt.where(AppointmentModel.doctor_id.in_(doctor_ids))
    if desde is not None:
        stmt = stmt.where(AppointmentModel.start_datetime >= desde)
    if hasta is not None:
        stmt = stmt.where(AppointmentModel.start_datetime < hasta)

    result = await db.execute(stmt.group_by(StatusModel.code))
    return {code: total for code, total in result.all()}


async def citas_del_dia(
    db: AsyncSession, *, doctor_ids: set[int] | None, dia: date
) -> list[AppointmentModel]:
    """Citas de un dia, con estado y paciente cargados."""
    if doctor_ids is not None and not doctor_ids:
        return []

    stmt = (
        select(AppointmentModel)
        .join(StatusModel, StatusModel.id == AppointmentModel.status_id)
        .where(
            AppointmentModel.start_datetime >= inicio_del_dia(dia),
            AppointmentModel.start_datetime < inicio_del_dia(dia + timedelta(days=1)),
        )
        .order_by(AppointmentModel.start_datetime)
    )
    if doctor_ids is not None:
        stmt = stmt.where(AppointmentModel.doctor_id.in_(doctor_ids))

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def citas_por_dia(
    db: AsyncSession, *, doctor_ids: set[int] | None, dias: int
) -> list[dict]:
    """Serie diaria para la grafica: total, atendidas, canceladas, inasistidas.

    Los dias sin citas no se omiten: una serie con huecos hace que un lunes
    tranquilo parezca un dia sin actividad.
    """
    if doctor_ids is not None and not doctor_ids:
        return []

    desde = inicio_del_dia(date.today() - timedelta(days=dias - 1))

    stmt = (
        select(
            func.date(AppointmentModel.start_datetime).label("dia"),
            StatusModel.code,
            func.count(AppointmentModel.id),
        )
        .join(StatusModel, StatusModel.id == AppointmentModel.status_id)
        .where(AppointmentModel.start_datetime >= desde)
        .group_by("dia", StatusModel.code)
    )
    if doctor_ids is not None:
        stmt = stmt.where(AppointmentModel.doctor_id.in_(doctor_ids))

    result = await db.execute(stmt)

    # codigo -> {dia: total}. Se acumulan aparte porque una cita cuenta en
    # un solo estado, pero la serie necesita el total de todos a la vez.
    acumulado: dict[str, dict[date, int]] = {}
    for dia, codigo, total in result.all():
        acumulado.setdefault(str(codigo), {})[dia] = total

    inasistencias = await _inasistencias_por_dia(db, doctor_ids=doctor_ids, desde=desde)

    serie = []
    for offset in range(dias):
        dia = date.today() - timedelta(days=dias - 1 - offset)
        serie.append(
            {
                "dia": dia.isoformat(),
                "total": sum(por_dia.get(dia, 0) for por_dia in acumulado.values()),
                "atendidas": acumulado.get("ATENDIDA", {}).get(dia, 0),
                "canceladas": acumulado.get("CANCELADA", {}).get(dia, 0),
                "inasistencias": inasistencias.get(dia, 0),
            }
        )
    return serie


async def _inasistencias_por_dia(
    db: AsyncSession, *, doctor_ids: set[int] | None, desde: datetime
) -> dict[date, int]:
    """Citas ya pasadas, sin nota medica y que siguen esperando turno."""
    if doctor_ids is not None and not doctor_ids:
        return {}

    sub_estados = select(StatusModel.id).where(StatusModel.code.in_(OCUPAN_AGENDA))
    sub_nota = select(MedicalNote.appointment_id)

    stmt = (
        select(
            func.date(AppointmentModel.start_datetime).label("dia"),
            func.count(AppointmentModel.id),
        )
        .where(
            AppointmentModel.status_id.in_(sub_estados),
            AppointmentModel.start_datetime < datetime.now(timezone.utc),
            AppointmentModel.start_datetime >= desde,
            AppointmentModel.id.not_in(sub_nota),
        )
        .group_by("dia")
    )
    if doctor_ids is not None:
        stmt = stmt.where(AppointmentModel.doctor_id.in_(doctor_ids))

    result = await db.execute(stmt)
    return {dia: total for dia, total in result.all()}
