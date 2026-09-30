"""Indicadores del dashboard: los numeros que se ven en las tarjetas.

Todo se calcula sobre el alcance que devuelve `crud_agenda_scope.alcance_de_agenda`,
de modo que un especialista ve sus numeros y un administrador los de la clinica
sin cambiar una sola consulta.

Ver `docs/FRONTEND.md`.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import crud_agenda_scope, crud_dashboard_metrics as metricas
from core import rbac
from models.appointment import Appointment as AppointmentModel
from models.appointment_status import AppointmentStatus as StatusModel
from models.doctor import Doctor as DoctorModel
from models.medical_note import MedicalNote
from models.patient import Patient
from models.user import User as UserModel


async def _conteo(
    db: AsyncSession, doctor_ids: set[int] | None, desde: datetime, hasta: datetime
) -> int:
    """Citas en un rango de tiempo, dentro del alcance."""
    if doctor_ids is not None and not doctor_ids:
        return 0
    stmt = select(func.count(AppointmentModel.id)).where(
        AppointmentModel.start_datetime >= desde,
        AppointmentModel.start_datetime < hasta,
    )
    if doctor_ids is not None:
        stmt = stmt.where(AppointmentModel.doctor_id.in_(doctor_ids))
    return int((await db.execute(stmt)).scalar() or 0)


async def indicadores(
    db: AsyncSession, user: UserModel, *, doctor_ids: set[int] | None
) -> dict:
    """Las tarjetas de arriba del dashboard.

    Las tasas se calculan sobre lo que ya ocurrio, no sobre el total: una cita
    de la manana que sigue sin atender no cuenta como inasistencia a las 8am.
    """
    ahora = datetime.now(timezone.utc)
    hoy = date.today()
    primero_del_mes = datetime(hoy.year, hoy.month, 1, tzinfo=timezone.utc)

    por_estado_hoy = await metricas.contar_por_estado(
        db,
        doctor_ids=doctor_ids,
        desde=metricas.inicio_del_dia(hoy),
        hasta=metricas.inicio_del_dia(hoy + timedelta(days=1)),
    )
    # Dos ventanas distintas y no una sola, porque responden a dos preguntas:
    #   - el mes COMPLETO es la carga de trabajo: incluye lo aun no ocurrido.
    #   - el mes HASTA AHORA es lo que puede dar tasas: lo futuro no ha pasado.
    por_estado_mes = await metricas.contar_por_estado(
        db, doctor_ids=doctor_ids, desde=primero_del_mes
    )
    por_estado_hasta_ahora = await metricas.contar_por_estado(
        db, doctor_ids=doctor_ids, desde=primero_del_mes, hasta=ahora
    )

    inasistencias = await _inasistencias(db, doctor_ids=doctor_ids, dias=30)
    atendidas = por_estado_hasta_ahora.get("ATENDIDA", 0)
    canceladas = por_estado_hasta_ahora.get("CANCELADA", 0)
    # El denominador es lo que ya se resolvio. `por_estado_mes` incluye estados
    # vivos (PENDIENTE, EN ESPERA) que todavia no pueden contarse como exito ni
    # como fracaso.
    resueltas = atendidas + canceladas + inasistencias

    return {
        "citas_hoy": sum(por_estado_hoy.values()),
        "citas_hoy_atendidas": por_estado_hoy.get("ATENDIDA", 0),
        "citas_hoy_pendientes": por_estado_hoy.get("PENDIENTE", 0),
        "citas_hoy_confirmadas": por_estado_hoy.get("CONFIRMADA", 0),
        "citas_hoy_en_espera": por_estado_hoy.get("EN ESPERA", 0),
        "citas_hoy_en_proceso": por_estado_hoy.get("EN PROCESO", 0),
        "citas_semana": await _conteo(
            db, doctor_ids, _lunes_de(ahora), _lunes_de(ahora) + timedelta(days=7)
        ),
        # Carga del mes completo, incluida la parte que aun no ha ocurrido.
        "citas_mes": sum(por_estado_mes.values()),
        "atendidas_mes": atendidas,
        "canceladas_mes": canceladas,
        "inasistencias_mes": inasistencias,
        "tasa_asistencia_pct": _pct(atendidas, resueltas),
        "tasa_cancelacion_pct": _pct(canceladas, resueltas),
        "tasa_inasistencia_pct": _pct(inasistencias, resueltas),
    }


async def _inasistencias(
    db: AsyncSession, *, doctor_ids: set[int] | None, dias: int
) -> int:
    """Citas ya pasadas que siguen esperando turno y sin nota medica.

    Misma definicion que el job `auto_cancel_no_show_appointments`, para que el
    panel y el job nunca se contradigan.
    """
    if doctor_ids is not None and not doctor_ids:
        return 0

    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    sub_estados = select(StatusModel.id).where(
        StatusModel.code.in_(metricas.OCUPAN_AGENDA)
    )
    sub_nota = select(MedicalNote.appointment_id)

    stmt = select(func.count(AppointmentModel.id)).where(
        AppointmentModel.status_id.in_(sub_estados),
        AppointmentModel.start_datetime < datetime.now(timezone.utc),
        AppointmentModel.start_datetime >= desde,
        AppointmentModel.id.not_in(sub_nota),
    )
    if doctor_ids is not None:
        stmt = stmt.where(AppointmentModel.doctor_id.in_(doctor_ids))
    return int((await db.execute(stmt)).scalar() or 0)


async def resumen_del_dia(
    db: AsyncSession, user: UserModel, *, doctor_ids: set[int] | None, dia: date
) -> dict:
    """Cabecera del dia: total, avance y los estados de la sala de espera."""
    por_estado = await metricas.contar_por_estado(
        db,
        doctor_ids=doctor_ids,
        desde=metricas.inicio_del_dia(dia),
        hasta=metricas.inicio_del_dia(dia + timedelta(days=1)),
    )
    total = sum(por_estado.values())
    en_curso = por_estado.get("EN ESPERA", 0) + por_estado.get("EN PROCESO", 0)
    cerradas = por_estado.get("ATENDIDA", 0) + por_estado.get("CANCELADA", 0)

    return {
        "fecha": dia.isoformat(),
        "total": total,
        "en_curso": en_curso,
        "cerradas": cerradas,
        "avance_pct": _pct(cerradas, total),
        "por_estado": por_estado,
    }


async def asignacion_del_asistente(
    db: AsyncSession, user: UserModel
) -> list[dict]:
    """Los especialistas que este asistente tiene asignados.

    Devuelve tambien los que todavia no tienen ficha de `doctors`: son un
    especialista real que el asistente coordina, aunque el alta quedara a medias.
    """
    from models.assistant_specialist import AssistantSpecialist

    result = await db.execute(
        select(
            AssistantSpecialist.specialist_id,
            UserModel.full_name,
            UserModel.email,
            UserModel.is_active,
            DoctorModel.id,
            Specialty.name,
        )
        .join(UserModel, UserModel.id == AssistantSpecialist.specialist_id)
        .outerjoin(
            DoctorModel, DoctorModel.email == UserModel.email
        )
        .outerjoin(Specialty, Specialty.id == DoctorModel.specialty_id)
        .where(AssistantSpecialist.assistant_id == user.id)
    )

    return [
        {
            "especialista_id": str(usuario),
            "nombre": nombre or "Sin nombre",
            "email": correo,
            "activo": bool(activo),
            "doctor_id": doctor_id,
            "especialidad": especialidad,
        }
        for usuario, nombre, correo, activo, doctor_id, especialidad in result.all()
    ]


async def alcance_de_este_usuario(db: AsyncSession, user: UserModel) -> dict:
    """Que ve este usuario en el panel. La UI lo usa para etiquetar la vista."""
    ids = await crud_agenda_scope.alcance_de_agenda(db, user)
    return {
        "es_admin": rbac.has_role(user, rbac.ADMIN_ROLES),
        "es_asistente": rbac.has_role(user, [rbac.ASSISTANT]),
        "es_medico": rbac.has_role(user, [rbac.DOCTOR, rbac.SPECIALIST]),
        "medicos_visibles": None if ids is None else len(ids),
    }


def _pct(parte: int, total: int) -> float:
    """Porcentaje redondeado. 0.0 cuando no hay denominador.

    Devolver 0 en vez de `None` evita que la UI muestre "NaN%" en una agenda
    vacia, que es el caso normal de un asistente sin asignaciones.
    """
    if not total:
        return 0.0
    return round(parte / total * 100, 1)


def _lunes_de(momento: datetime) -> datetime:
    """Lunes a las 00:00 de la semana que contiene `momento`."""
    dia = momento.date() - timedelta(days=momento.weekday())
    return datetime.combine(dia, datetime.min.time(), tzinfo=timezone.utc)
