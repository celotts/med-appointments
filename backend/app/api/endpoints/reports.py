"""Reporting and dashboard endpoints."""

from typing import Any

from dependencies import get_current_user, get_db
from dependencies_i18n import I18nResponse, get_language
from fastapi import APIRouter, Depends, Query
from models.user import User as UserModel
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["Reports & Dashboard"])


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
    "/dashboard/summary",
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
            """
            SELECT
                (SELECT COUNT(*) FROM patients WHERE deleted_at IS NULL) AS total_patients,
                (SELECT COUNT(*) FROM doctors WHERE deleted_at IS NULL) AS total_doctors,
                (SELECT COUNT(*) FROM appointments
                 WHERE DATE(start_datetime) = CURRENT_DATE
                   AND status_id != (SELECT id FROM appointment_statuses WHERE code = 'CANCELADA')
                ) AS total_appointments_today,
                (SELECT COUNT(*) FROM appointments
                 WHERE start_datetime >= DATE_TRUNC('week', NOW())
                   AND start_datetime < DATE_TRUNC('week', NOW()) + INTERVAL '7 days'
                   AND status_id != (SELECT id FROM appointment_statuses WHERE code = 'CANCELADA')
                ) AS total_appointments_week,
                (SELECT COUNT(*) FROM appointments
                 WHERE start_datetime >= DATE_TRUNC('month', NOW())
                   AND start_datetime < DATE_TRUNC('month', NOW()) + INTERVAL '1 month'
                   AND status_id != (SELECT id FROM appointment_statuses WHERE code = 'CANCELADA')
                ) AS total_appointments_month,
                (SELECT COUNT(*) FROM appointments
                 WHERE status_id = (SELECT id FROM appointment_statuses WHERE code = 'PENDIENTE')
                ) AS appointments_pending,
                (SELECT COUNT(*) FROM appointments
                 WHERE status_id = (SELECT id FROM appointment_statuses WHERE code = 'CONFIRMADA')
                ) AS appointments_confirmed,
                (SELECT COUNT(*) FROM appointments
                 WHERE DATE(start_datetime) = CURRENT_DATE
                   AND status_id = (SELECT id FROM appointment_statuses WHERE code = 'COMPLETADA')
                ) AS appointments_completed_today,
                (SELECT COUNT(*) FROM appointments
                 WHERE start_datetime >= DATE_TRUNC('month', NOW())
                   AND status_id = (SELECT id FROM appointment_statuses WHERE code = 'CANCELADA')
                ) AS appointments_cancelled_month
            """
        )
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
    days: int = Query(7, ge=1, le=90),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns appointment count grouped by day for the last N days."""
    result = await db.execute(
        text(
            """
            SELECT DATE(start_datetime) AS day,
                   COUNT(*) AS total,
                   SUM(CASE WHEN ec.code = 'COMPLETADA' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN ec.code = 'CANCELADA' THEN 1 ELSE 0 END) AS cancelled
            FROM appointments c
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.start_datetime >= NOW() - INTERVAL ':days days'
            GROUP BY day
            ORDER BY day
            """
        ),
        {"days": days},
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
                   SUM(CASE WHEN ec.code = 'COMPLETADA' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN ec.code = 'CANCELADA' THEN 1 ELSE 0 END) AS cancelled
            FROM appointments c
            JOIN doctors m ON m.id = c.doctor_id
            JOIN specialties e ON e.id = m.specialty_id
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.start_datetime >= NOW() - INTERVAL ':days days'
            GROUP BY doctor, specialty
            ORDER BY total_appointments DESC
            """
        ),
        {"days": days},
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
    """Returns no-show rate statistics."""
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN ec.code = 'COMPLETADA' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN ec.code = 'CANCELADA' THEN 1 ELSE 0 END) AS cancelled,
                   SUM(CASE WHEN ec.code = 'PENDIENTE' THEN 1 ELSE 0 END) AS pending
            FROM appointments c
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.start_datetime >= NOW() - INTERVAL ':days days'
            """
        ),
        {"days": days},
    )
    row = result.mappings().first()

    total = row["total"] or 0
    completed = row["completed"] or 0
    cancelled = row["cancelled"] or 0

    i18n = I18nResponse(language)
    return {
        "period": i18n.get("last_days", days=days),
        "total_appointments": total,
        "completed": completed,
        "cancelled": cancelled,
        "attendance_rate": f"{(completed / total * 100):.1f}%" if total > 0 else "0%",
        "cancellation_rate": f"{(cancelled / total * 100):.1f}%" if total > 0 else "0%",
    }


@router.get(
    "/reports/export/csv",
    summary="Export appointments as CSV",
)
async def export_appointments_csv(
    *,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Exports appointments data as CSV format."""
    import csv
    import io

    from fastapi.responses import StreamingResponse

    result = await db.execute(
        text(
            """
            SELECT c.id, c.start_datetime, c.end_datetime,
                   CONCAT(p.first_name, ' ', p.last_name) AS patient,
                   CONCAT(m.first_name, ' ', m.last_name) AS doctor,
                   e.name AS specialty,
                   ec.code AS status,
                   c.reason
            FROM appointments c
            JOIN patients p ON p.id = c.patient_id
            JOIN doctors m ON m.id = c.doctor_id
            JOIN specialties e ON e.id = m.specialty_id
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.start_datetime >= NOW() - INTERVAL ':days days'
            ORDER BY c.start_datetime DESC
            """
        ),
        {"days": days},
    )
    rows = result.mappings().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["ID", "Start", "End", "Patient", "Doctor", "Specialty", "Status", "Reason"]
    )

    for row in rows:
        writer.writerow(
            [
                row["id"],
                str(row["start_datetime"]),
                str(row["end_datetime"]),
                row["patient"],
                row["doctor"],
                row["specialty"],
                row["status"],
                row["reason"],
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=appointments_export.csv"},
    )
