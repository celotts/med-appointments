"""Dashboard operativo para quien lleva la agenda.

Un endpoint por pregunta, no un `summary` con todo mezclado: cada uno se puede
cachear, testear y consumir por separado segun lo que la pantalla necesite.

## Alcance

Todo lo que se devuelve pasa por `crud_agenda_scope.alcance_de_agenda`:

| Rol | Que ve |
|---|---|
| DOCTOR / SPECIALIST | su propia agenda |
| ASSISTANT | la de los especialistas que tiene asignados |
| ADMIN / SUPER_ADMIN | toda la clinica |

Un `PATIENT` recibe 403 en todos: el panel es una herramienta de trabajo del
personal clinico, no un resumen de sus propias citas.

Los roles se validan con `require_roles(*rbac.DASHBOARD_ROLES)`, nunca con
comparaciones manuales.

Ver `docs/FRONTEND.md`.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from core import crud_agenda_scope, rbac
from core import crud_calendario as calendrio
from core import crud_dashboard_kpis as kpis
from core import crud_dashboard_metrics as metricas
from core import crud_dashboard_workload as workload
from dependencies import get_db, require_roles
from fastapi import APIRouter, Depends, Query
from models.user import User as UserModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

# Todos los endpoints del panel exigen un rol de DASHBOARD_ROLES. Se declara
# una vez aqui para que anadir un rol al panel sea cambiar una linea.
require_dashboard = require_roles(*rbac.DASHBOARD_ROLES)


@router.get("/scope", summary="Que ve este usuario en el panel")
async def ver_scope(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_dashboard),
) -> dict[str, Any]:
    """Alcance del panel: rol, y cuantos medicos ve.

    La UI lo consulta al montar para etiquetar la vista ("Agenda de clinica"
    frente a "Agenda del Dr. Perez") y para no pintar secciones vacias.
    """
    return await kpis.alcance_de_este_usuario(db, current_user)


@router.get("/kpis", summary="Indicadores del panel")
async def ver_kpis(
    db: AsyncSession = Depends(get_db),
    dias: int = Query(30, ge=1, le=365, description="Ventana de las tasas"),
    current_user: UserModel = Depends(require_dashboard),
) -> dict[str, Any]:
    """Tarjetas principales: citas de hoy, semana, mes y tasas."""
    ids = await crud_agenda_scope.alcance_de_agenda(db, current_user)
    return await kpis.indicadores(db, current_user, doctor_ids=ids)


@router.get("/today", summary="Resumen del dia")
async def ver_hoy(
    db: AsyncSession = Depends(get_db),
    fecha: date | None = Query(None, description="Dia en formato YYYY-MM-DD"),
    current_user: UserModel = Depends(require_dashboard),
) -> dict[str, Any]:
    """Como va el dia: total, cuantos se resolvieron y la sala de espera."""
    ids = await crud_agenda_scope.alcance_de_agenda(db, current_user)
    return await kpis.resumen_del_dia(
        db, current_user, doctor_ids=ids, dia=fecha or date.today()
    )


@router.get("/series", summary="Serie diaria para la grafica")
async def ver_serie(
    db: AsyncSession = Depends(get_db),
    dias: int = Query(14, ge=7, le=90),
    current_user: UserModel = Depends(require_dashboard),
) -> dict[str, Any]:
    """Citas por dia: total, atendidas, canceladas e inasistencias.

    Los dias sin citas vienen con total 0 en vez de omitirse: una serie con
    huecos hace que un lunes tranquilo parezca un dia sin actividad.
    """
    ids = await crud_agenda_scope.alcance_de_agenda(db, current_user)
    return {
        "dias": dias,
        "data": await metricas.citas_por_dia(db, doctor_ids=ids, dias=dias),
    }


@router.get("/workload", summary="Carga por medico")
async def ver_carga(
    db: AsyncSession = Depends(get_db),
    dias: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(require_dashboard),
) -> dict[str, Any]:
    """Carga por medico con su ocupacion.

    `ocupacion_pct` es None cuando el medico no tiene horario en
    `doctor_schedules`: no se puede calcular, que no es lo mismo que 0%.
    """
    ids = await crud_agenda_scope.alcance_de_agenda(db, current_user)
    return {
        "dias": dias,
        "data": await workload.carga_por_medico(db, doctor_ids=ids, dias=dias),
    }


@router.get("/calendario", summary="Calendario: dias con citas y su estado")
async def ver_calendario(
    db: AsyncSession = Depends(get_db),
    # `0` significa "el actual". El rango arranca en 1 porque `Query(0)` con
    # `ge=1970` rechazaba el propio default que se queria permitir.
    mes: int = Query(0, ge=0, le=12, description="Mes (1-12). 0 = el actual"),
    anio: int = Query(0, ge=0, le=2100, description="Ano. 0 = el actual"),
    current_user: UserModel = Depends(require_dashboard),
) -> dict[str, Any]:
    """La rejilla del mes con el desglose por estado de cada dia.

    Un total por dia no basta para agendar: un dia con 10 citas de las que 8
    estan confirmadas no es igual que uno con 10 pendientes, y de eso depende
    si hay que llamar a alguien. Por eso cada dia trae el desglose.

    Se devuelve la malla completa (filas de 7) con los dias del mes anterior y
    siguiente que se completan en la rejilla, para que el calendario no tenga
    que reconstruirlos y no "baille" al cambiar de mes.
    """
    hoy = date.today()
    mes_efectivo = mes or hoy.month
    anio_efectivo = anio or hoy.year

    primero, siguiente = calendrio.dias_del_mes(anio_efectivo, mes_efectivo)
    malla = calendrio.malla_del_mes(anio_efectivo, mes_efectivo)

    ids = await crud_agenda_scope.alcance_de_agenda(db, current_user)
    puntos = await calendrio.rango_por_dia(
        db, doctor_ids=ids, desde=malla[0], hasta=malla[-1] + timedelta(days=1)
    )

    return {
        "anio": anio_efectivo,
        "mes": mes_efectivo,
        "primera_semana": malla[0].weekday(),
        "dias_en_mes": (siguiente - primero).days,
        "dias": puntos,
    }


@router.get("/schedule", summary="Agenda del dia")
async def ver_agenda(
    db: AsyncSession = Depends(get_db),
    fecha: date | None = Query(None, description="Dia en formato YYYY-MM-DD"),
    current_user: UserModel = Depends(require_dashboard),
) -> dict[str, Any]:
    """Las citas del dia, ordenadas por hora.

    Devuelve datos planos y no entidades de SQLAlchemy a proposito: la pantalla
    necesita paciente, hora y estado, y nada mas. Cada campo del mapa es
    explicito para que un cambio en el modelo no rompa la respuesta en silencio.
    """
    from sqlalchemy import select

    from models.appointment_status import AppointmentStatus
    from models.patient import Patient

    ids = await crud_agenda_scope.alcance_de_agenda(db, current_user)
    dia = fecha or date.today()
    citas = await metricas.citas_del_dia(db, doctor_ids=ids, dia=dia)

    if not citas:
        return {"fecha": dia.isoformat(), "total": 0, "citas": []}

    estados = {
        id_: {"code": code, "description": descripcion}
        for id_, code, descripcion in (
            await db.execute(
                select(
                    AppointmentStatus.id,
                    AppointmentStatus.code,
                    AppointmentStatus.description,
                ).where(
                    AppointmentStatus.id.in_({c.status_id for c in citas})
                )
            )
        ).all()
    }
    pacientes = {
        id_: {"nombre": f"{nombre} {apellido}".strip(), "documento": documento}
        for id_, nombre, apellido, documento in (
            await db.execute(
                select(
                    Patient.id,
                    Patient.first_name,
                    Patient.last_name,
                    Patient.document_number,
                ).where(Patient.id.in_({c.patient_id for c in citas}))
            )
        ).all()
    }

    return {
        "fecha": dia.isoformat(),
        "total": len(citas),
        "citas": [
            {
                "id": cita.id,
                "hora_inicio": cita.start_datetime.isoformat(),
                "hora_fin": cita.end_datetime.isoformat(),
                "estado": estados.get(cita.status_id, {}).get("code"),
                "estado_descripcion": estados.get(cita.status_id, {}).get("description"),
                "paciente": pacientes.get(cita.patient_id, {}).get("nombre", "Paciente"),
                "paciente_documento": pacientes.get(cita.patient_id, {}).get("documento"),
                "doctor_id": cita.doctor_id,
                "motivo": cita.reason,
            }
            for cita in citas
        ],
    }
