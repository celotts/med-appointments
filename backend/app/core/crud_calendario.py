"""Calendario: que dias tienen citas y en que estado.

## Para que sirve

Un especialista necesita responder dos preguntas antes de agendar: **que dias
tengo occupied** y **como estan esos pacientes**. Un total por dia no basta: un
dia con 10 citas, 8 confirmadas y 2 pendientes no es igual que uno con 10
pendientes, y para una agenda clinica la diferencia es si hay que llamar a
alguien.

Por eso el desglose es por estado y no un `total`: el calendario pinta el dia
con la mezcla real.

## El rango se pide completo, no se rellena

Un calendario de mes necesita los dias del mes aunque no tengan citas (para
mostrarlos vacios) y algunos del mes anterior/siguiente (las celdas que se
completan). Por eso `rango_por_dia` devuelve un punto POR DIA dentro del rango,
con los estados vacios en cero.

Un `GROUP BY dia` sin dias de relleno produce huecos: el lunes tranquilo
desaparece y el mes aparece con huecos que el usuario lee como "sin datos" en
vez de "sin citas".

Ver `docs/FRONTEND.md`.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.appointment import Appointment as AppointmentModel
from models.appointment_status import AppointmentStatus as StatusModel

# Los 8 estados canonicos. El calendario los recorre siempre, para que la
# leyenda no cambie de una carga a otra.
ESTADOS_CANONICOS = (
    "PENDIENTE",
    "CONFIRMADA",
    "EN ESPERA",
    "EN PROCESO",
    "ATENDIDA",
    "CANCELADA",
    "SUSPENDIDA",
    "REAGENDADA",
)


async def rango_por_dia(
    db: AsyncSession,
    *,
    doctor_ids: set[int] | None,
    desde: date,
    hasta: date,
) -> list[dict]:
    """Un punto por dia en `[desde, hasta)`, con el desglose por estado.

    `hasta` es EXCLUSIVO, igual que en SQL. Un rango de 30 dias son 30 puntos.
    """
    if doctor_ids is not None and not doctor_ids:
        # Sin alcance no hay nada que ver, pero se devuelven los dias vacios:
        # el calendario necesita el mes dibujado para poder navegarlo.
        return [_dia_vacio(d) for d in _rango(desde, hasta)]

    inicio = date.fromisoformat(desde.isoformat())
    stmt = (
        select(
            func.date(AppointmentModel.start_datetime).label("dia"),
            StatusModel.code,
            func.count(AppointmentModel.id),
        )
        .join(StatusModel, StatusModel.id == AppointmentModel.status_id)
        .where(
            AppointmentModel.start_datetime >= inicio,
            AppointmentModel.start_datetime < hasta,
        )
        .group_by("dia", StatusModel.code)
    )
    if doctor_ids is not None:
        stmt = stmt.where(AppointmentModel.doctor_id.in_(doctor_ids))

    result = await db.execute(stmt)

    por_estado: dict[str, dict[date, int]] = {}
    for dia, codigo, total in result.all():
        por_estado.setdefault(str(codigo), {})[dia] = total

    puntos = []
    for d in _rango(desde, hasta):
        por_estado_del_dia = {
            codigo: valores.get(d, 0) for codigo, valores in por_estado.items()
        }
        puntos.append(
            {
                "dia": d.isoformat(),
                "total": sum(por_estado_del_dia.values()),
                "por_estado": {
                    estado: por_estado_del_dia.get(estado, 0)
                    for estado in ESTADOS_CANONICOS
                },
                # Derivadas, para que el frontend no las recalcule (ni las
                # calcule de forma subtly distinta).
                "confirmadas": por_estado_del_dia.get("CONFIRMADA", 0),
                "pendientes": por_estado_del_dia.get("PENDIENTE", 0),
                "atendidas": por_estado_del_dia.get("ATENDIDA", 0),
                "canceladas": por_estado_del_dia.get("CANCELADA", 0),
            }
        )
    return puntos


def _rango(desde: date, hasta: date):
    d = desde
    while d < hasta:
        yield d
        d += timedelta(days=1)


def _dia_vacio(d: date) -> dict:
    return {
        "dia": d.isoformat(),
        "total": 0,
        "por_estado": {estado: 0 for estado in ESTADOS_CANONICOS},
        "confirmadas": 0,
        "pendientes": 0,
        "atendidas": 0,
        "canceladas": 0,
    }


def dias_del_mes(anio: int, mes: int) -> tuple[date, date]:
    """Primer y primer dia del mes siguiente, para usar como rango.

    `mes` va de 1 a 12. Devolver el primer dia del mes siguiente es lo que
    hace que diciembre termine bien: `date(2026, 12, 1)` + 1 mes = enero.
    """
    primero = date(anio, mes, 1)
    if mes == 12:
        siguiente = date(anio + 1, 1, 1)
    else:
        siguiente = date(anio, mes + 1, 1)
    return primero, siguiente


def malla_del_mes(anio: int, mes: int) -> list[date]:
    """Los dias que pintan las celdas del mes, filas completas de 7.

    Empieza en el lunes de la semana del dia 1 y termina en el domingo de la
    semana del ultimo dia. Son siempre multiplos de 7, que es lo que hace que
    la rejilla no "baille" al cambiar de mes.
    """
    primero, siguiente = dias_del_mes(anio, mes)
    ultimo = siguiente - timedelta(days=1)

    inicio = primero - timedelta(days=primero.weekday())  # weekday(): 0 = lunes
    fin = ultimo + timedelta(days=6 - ultimo.weekday())
    return list(_rango(inicio, fin + timedelta(days=1)))


__all__ = [
    "rango_por_dia",
    "dias_del_mes",
    "malla_del_mes",
    "ESTADOS_CANONICOS",
]
