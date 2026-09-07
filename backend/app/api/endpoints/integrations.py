"""Integration endpoints: Calendar sync, Multi-sede, Roles."""

from typing import Any

from dependencies import get_current_user, get_db
from dependencies_i18n import get_language, I18nResponse
from fastapi import APIRouter, Depends, HTTPException, Query
from models.user import User as UserModel
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["Integrations"])


# ============================================================================
# CALENDAR SYNC
# ============================================================================


class CalendarEvent(BaseModel):
    title: str
    start: str  # ISO 8601
    end: str  # ISO 8601
    description: str = ""
    location: str = ""


@router.get(
    "/calendar/sync/{doctor_id}",
    summary="Get calendar events for a doctor",
)
async def get_calendar_events(
    *,
    db: AsyncSession = Depends(get_db),
    doctor_id: int,
    days: int = Query(30, ge=1, le=90),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns appointments in calendar format (Google Calendar compatible)."""
    result = await db.execute(
        text(
            """
            SELECT c.id, c.start_datetime, c.end_datetime,
                   CONCAT(p.first_name, ' ', p.last_name) AS patient,
                   c.reason,
                   CONCAT(m.first_name, ' ', m.last_name) AS doctor
            FROM appointments c
            JOIN patients p ON p.id = c.patient_id
            JOIN doctors m ON m.id = c.doctor_id
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.doctor_id = :doctor_id
              AND c.start_datetime >= NOW()
              AND c.start_datetime < NOW() + INTERVAL ':days days'
              AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
            ORDER BY c.start_datetime
            """
        ),
        {"doctor_id": doctor_id, "days": days},
    )
    appointments = result.mappings().all()

    events = []
    for apt in appointments:
        events.append({
            "id": f"apt_{apt['id']}",
            "summary": f"Appointment: {apt['patient']}",
            "description": apt["reason"] or "Medical appointment",
            "start": {
                "dateTime": str(apt["start_datetime"]),
                "timeZone": "America/Mexico_City",
            },
            "end": {
                "dateTime": str(apt["end_datetime"]),
                "timeZone": "America/Mexico_City",
            },
            "attendees": [
                {"email": apt["patient"].lower().replace(" ", ".") + "@placeholder.com"}
            ],
        })

    return {
        "doctor_id": doctor_id,
        "total_events": len(events),
        "events": events,
        "format": "Google Calendar JSON",
    }


@router.get(
    "/calendar/ical/{doctor_id}",
    summary="Export calendar as iCal format",
)
async def export_ical(
    *,
    db: AsyncSession = Depends(get_db),
    doctor_id: int,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Exports appointments in iCal format (.ics) for any calendar app."""
    from fastapi.responses import PlainTextResponse

    result = await db.execute(
        text(
            """
            SELECT c.id, c.start_datetime, c.end_datetime,
                   CONCAT(p.first_name, ' ', p.last_name) AS patient,
                   c.reason
            FROM appointments c
            JOIN patients p ON p.id = c.patient_id
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE c.doctor_id = :doctor_id
              AND c.start_datetime >= NOW()
              AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
            ORDER BY c.start_datetime
            """
        ),
        {"doctor_id": doctor_id},
    )
    appointments = result.mappings().all()

    ical_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MedAppointments//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for apt in appointments:
        start = apt["start_datetime"].strftime("%Y%m%dT%H%M%S")
        end = apt["end_datetime"].strftime("%Y%m%dT%H%M%S")
        ical_lines.extend([
            "BEGIN:VEVENT",
            f"UID:apt_{apt['id']}@medappointments.com",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"SUMMARY:Appointment - {apt['patient']}",
            f"DESCRIPTION:{apt['reason'] or 'Medical appointment'}",
            "END:VEVENT",
        ])

    ical_lines.append("END:VCALENDAR")

    return PlainTextResponse(
        "\n".join(ical_lines),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=appointments.ics"},
    )


# ============================================================================
# MULTI-SEDE
# ============================================================================


@router.get(
    "/branches",
    summary="List all branches",
)
async def list_branches(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Lists all clinic branches."""
    result = await db.execute(
        text("SELECT * FROM branches WHERE deleted_at IS NULL")
    )
    branches = result.mappings().all()
    return {"total": len(branches), "branches": [dict(b) for b in branches]}


@router.get(
    "/branches/{branch_id}/doctors",
    summary="List doctors at a specific branch",
)
async def get_doctors_by_branch(
    *,
    db: AsyncSession = Depends(get_db),
    branch_id: int,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns doctors working at a specific branch."""
    result = await db.execute(
        text(
            """
            SELECT m.id, CONCAT(m.first_name, ' ', m.last_name) AS name,
                   e.name AS specialty, m.email, m.phone
            FROM doctors m
            JOIN specialties e ON e.id = m.specialty_id
            WHERE m.branch_id = :branch_id
            ORDER BY m.last_name, m.first_name
            """
        ),
        {"branch_id": branch_id},
    )
    doctors = result.mappings().all()
    return {"branch_id": branch_id, "total": len(doctors), "doctors": [dict(d) for d in doctors]}


# ============================================================================
# ROLES & PERMISSIONS
# ============================================================================


@router.get(
    "/roles",
    summary="List all roles",
)
async def list_roles(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Lists all system roles."""
    result = await db.execute(text("SELECT id, name FROM roles WHERE deleted_at IS NULL"))
    roles = result.mappings().all()

    return {
        "roles": [dict(r) for r in roles],
        "example_permissions": {
            "ADMIN": ["create_appointment", "edit_appointment", "cancel_appointment", "view_reports", "manage_users"],
            "RECEPTIONIST": ["create_appointment", "edit_appointment", "view_appointments"],
            "DOCTOR": ["view_appointments", "edit_status", "view_notes"],
            "PATIENT": ["view_my_appointments", "cancel_my_appointment"],
        },
    }


@router.get(
    "/users/{user_id}/permissions",
    summary="Get user permissions",
)
async def get_user_permissions(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: str,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Returns permissions for a specific user based on their role."""
    i18n = I18nResponse(language)
    result = await db.execute(
        text(
            """
            SELECT u.id, u.email, u.full_name, r.name AS role_name
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    user = result.mappings().first()

    if not user:
        raise i18n.error("not_found", status_code=404)

    # Permission mapping
    permissions_map = {
        "SUPER_ADMIN": [
            "create_appointment", "edit_appointment", "cancel_appointment", "reschedule_appointment",
            "view_reports", "manage_users", "manage_doctors",
            "view_all_appointments", "configure_system",
        ],
        "ADMIN": [
            "create_appointment", "edit_appointment", "cancel_appointment", "reschedule_appointment",
            "view_reports", "manage_users", "view_all_appointments",
        ],
        "RECEPCIONISTA": [
            "create_appointment", "edit_appointment", "cancel_appointment", "view_appointments",
        ],
        "DOCTOR": [
            "view_appointments", "edit_status", "view_notes", "edit_notes",
        ],
        "PATIENT": [
            "view_my_appointments", "cancel_my_appointment",
        ],
    }

    return {
        "user_id": user_id,
        "email": user["email"],
        "name": user["full_name"],
        "role": user["role_name"],
        "permissions": permissions_map.get(user["role_name"], []),
    }
