"""Reporting and dashboard endpoints.

## Codigos de estado: un solo vocabulario

Este modulo estaba roto: filtraba por `code = 'SCHEDULED' | 'CONFIRMED' |
'COMPLETED' | 'CANCELLED'`, y la BD solo tiene los 8 codigos en español
(`PENDIENTE`, `CONFIRMADA`, `EN ESPERA`, `EN PROCESO`, `ATENDIDA`, `CANCELADA`,
`SUSPENDIDA`, `REAGENDADA`). El subescalar devolvia NULL, `status_id != NULL`
evaluaba a NULL y el `WHERE` descartaba todas las filas: 7 de los 9 campos del
summary devolvian 0 siempre.

Los codigos vienen ahora de `AppointmentStatusCode`, el enum que ya es fuente
de verdad en `schemas/appointment.py:10-23`. Si mañana cambia un estado, este
modulo avisa con un ImportError en vez de devolver ceros en silencio.

Ver `docs/ESTADOS_CITA.md`.
"""

from typing import Any

from dependencies import get_current_user, get_db
from dependencies_i18n import I18nResponse, get_language
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from schemas.appointment import AppointmentStatusCode
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User as UserModel

router = APIRouter(prefix="/api/v1", tags=["Reports & Dashboard"])

# Codigos canonicos. No escribir literales: salen del enum.
_PENDING = AppointmentStatusCode.PENDING.value
_CONFIRMED = AppointmentStatusCode.CONFIRMED.value
_ATTENDED = AppointmentStatusCode.ATTENDED.value
_CANCELLED = AppointmentStatusCode.CANCELLED.value
_RESCHEDULED = AppointmentStatusCode.RESCHEDULED.value


class DashboardSummary(BaseModel):
    total_patients: int
    total_doctors: int
    total_appointments_today: int
    total_appointments_week: int
    total_appointments_month: int
    appointments_pending: int
    appointments_confirmed: int
    appointments_completed_today: int
    appointments_cancelled_month: int


@router.get(
    "/reports/dashboard/summary",
    response_model=DashboardSummary,
    summary="Get dashboard summary",
)
async def get_dashboard_summary(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns key metrics for the dashboard."""
    result = await db.execute(
        text(
            f"""
            SELECT
                (SELECT COUNT(*) FROM patients) AS total_patients,
                (SELECT COUNT(*) FROM doctors) AS total_doctors,
                (SELECT COUNT(*) FROM appointments
                 WHERE DATE(start_datetime) = CURRENT_DATE
                   AND status_id != (SELECT id FROM appointment_statuses WHERE code = :cancelada)
                ) AS total_appointments_today,
                (SELECT COUNT(*) FROM appointments
                 WHERE start_datetime >= DATE_TRUNC('week', NOW())
                   AND start_datetime < DATE_TRUNC('week', NOW()) + INTERVAL '7 days'
                   AND status_id != (SELECT id FROM appointment_statuses WHERE code = :cancelada)
                ) AS total_appointments_week,
                (SELECT COUNT(*) FROM appointments
                 WHERE start_datetime >= DATE_TRUNC('month', NOW())
                   AND start_datetime < DATE_TRUNC('month', NOW()) + INTERVAL '1 month'
                   AND status_id != (SELECT id FROM appointment_statuses WHERE code = :cancelada)
                ) AS total_appointments_month,
                (SELECT COUNT(*) FROM appointments
                 WHERE status_id = (SELECT id FROM appointment_statuses WHERE code = :pendiente)
                ) AS appointments_pending,
                (SELECT COUNT(*) FROM appointments
                 WHERE status_id = (SELECT id FROM appointment_statuses WHERE code = :confirmada)
                ) AS appointments_confirmed,
                (SELECT COUNT(*) FROM appointments
                 WHERE DATE(start_datetime) = CURRENT_DATE
                   AND status_id = (SELECT id FROM appointment_statuses WHERE code = :atendida)
                ) AS appointments_completed_today,
                (SELECT COUNT(*) FROM appointments
                 WHERE start_datetime >= DATE_TRUNC('month', NOW())
                   AND status_id = (SELECT id FROM appointment_statuses WHERE code = :cancelada)
                ) AS appointments_cancelled_month
            """
        ),
        {
            "cancelada": _CANCELLED,
            "pendiente": _PENDING,
            "confirmada": _CONFIRMED,
            "atendida": _ATTENDED,
        },
    )
    row = result.mappings().first()
    return row


@router.get(
    "/reports/appointments-by-day",
    summary="Get appointments grouped by day",
)
async def get_appointments_by_day(
    *,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=365),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns appointment count grouped by day for the last N days."""
    result = await db.execute(
        text(
            """
            SELECT DATE(start_datetime) AS day,
                   COUNT(*) AS total,
                   SUM(CASE WHEN ec.code = :atendida THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN ec.code = :cancelada THEN 1 ELSE 0 END) AS cancelled
            FROM appointments c
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.start_datetime >= NOW() - make_interval(days => :dias)
            GROUP BY day
            ORDER BY day
            """
        ),
        {"atendida": _ATTENDED, "cancelada": _CANCELLED, "dias": days},
    )
    data = result.mappings().all()
    i18n = I18nResponse(language)
    return {"period": i18n.get("last_days", days=days), "data": [dict(r) for r in data]}


@router.get(
    "/reports/appointments-by-doctor",
    summary="Get appointments grouped by doctor",
)
async def get_appointments_by_doctor(
    *,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns appointment count grouped by doctor."""
    result = await db.execute(
        text(
            """
            SELECT CONCAT(m.first_name, ' ', m.last_name) AS doctor,
                   e.name AS specialty,
                   COUNT(*) AS total_appointments,
                   SUM(CASE WHEN ec.code = :atendida THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN ec.code = :cancelada THEN 1 ELSE 0 END) AS cancelled
            FROM appointments c
            JOIN doctors m ON m.id = c.doctor_id
            JOIN specialties e ON e.id = m.specialty_id
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.start_datetime >= NOW() - make_interval(days => :dias)
            GROUP BY doctor, specialty
            ORDER BY total_appointments DESC
            """
        ),
        {"atendida": _ATTENDED, "cancelada": _CANCELLED, "dias": days},
    )
    data = result.mappings().all()
    i18n = I18nResponse(language)
    return {"period": i18n.get("last_days", days=days), "data": [dict(r) for r in data]}


@router.get(
    "/reports/no-show-rate",
    summary="Get no-show rate statistics",
)
async def get_no_show_rate(
    *,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns no-show rate statistics.

    La inasistencia no es "todo lo que no esta ATENDIDA": una cita de manana
    que sigue PENDIENTE no es un no-show. Se cuenta solo lo que ya paso su hora
    y no tiene nota medica, la misma definicion que aplica el job
    `auto_cancel_no_show_appointments`.
    """
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN ec.code = :atendida THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN ec.code = :cancelada THEN 1 ELSE 0 END) AS cancelled,
                   SUM(CASE WHEN ec.code = :pendiente THEN 1 ELSE 0 END) AS pending
            FROM appointments c
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.start_datetime >= NOW() - make_interval(days => :dias)
            """
        ),
        {
            "atendida": _ATTENDED,
            "cancelada": _CANCELLED,
            "pendiente": _PENDING,
            "dias": days,
        },
    )
    row = result.mappings().first()

    total = row["total"] or 0
    completed = row["completed"] or 0
    cancelled = row["cancelled"] or 0
    pending = row["pending"] or 0

    i18n = I18nResponse(language)
    return {
        "period": i18n.get("last_days", days=days),
        "total_appointments": total,
        "completed": completed,
        "cancelled": cancelled,
        "pending": pending,
        "attendance_rate": f"{(completed / total * 100):.1f}%" if total > 0 else "0%",
        "cancellation_rate": f"{(cancelled / total * 100):.1f}%" if total > 0 else "0%",
    }
