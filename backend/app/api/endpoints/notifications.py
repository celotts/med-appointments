"""Notification endpoints."""

from typing import Any

from dependencies import get_current_user, get_db
from dependencies_i18n import I18nResponse, get_language
from fastapi import APIRouter, Depends
from models.user import User as UserModel
from pydantic import BaseModel, EmailStr
from services.notifications import notification_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["Notifications"])


class SendNotificationRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    html: bool = True


class AppointmentNotificationRequest(BaseModel):
    patient_name: str
    doctor_name: str
    date: str
    reason: str
    notification_type: str  # confirmation, reminder, cancellation, reschedule


@router.post(
    "/notifications/send",
    summary="Send custom email notification",
)
async def send_notification(
    *,
    db: AsyncSession = Depends(get_db),
    request: SendNotificationRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Sends a custom email notification."""
    result = await notification_service.send_email(
        to=request.to,
        subject=request.subject,
        body=request.body,
        html=request.html,
    )
    return result


@router.post(
    "/notifications/appointment",
    summary="Send appointment-related notification",
)
async def send_appointment_notification(
    *,
    db: AsyncSession = Depends(get_db),
    request: AppointmentNotificationRequest,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Sends appointment notification (confirmation, reminder, cancellation, reschedule)."""
    i18n = I18nResponse(language)
    notification_type = request.notification_type.lower()

    if notification_type == "confirmation":
        subject, body = notification_service.generate_appointment_confirmation(
            request.patient_name,
            request.doctor_name,
            request.date,
            request.reason,
        )
    elif notification_type == "reminder":
        subject, body = notification_service.generate_appointment_reminder(
            request.patient_name,
            request.doctor_name,
            request.date,
        )
    elif notification_type == "cancellation":
        subject, body = notification_service.generate_cancellation_notice(
            request.patient_name,
            request.doctor_name,
            request.date,
            request.reason,
        )
    elif notification_type == "reschedule":
        subject, body = notification_service.generate_reschedule_notice(
            request.patient_name,
            request.doctor_name,
            request.date,
            request.reason,
        )
    else:
        raise i18n.error("invalid_notification_type", status_code=400)

    return {
        "notification_type": notification_type,
        "subject": subject,
        "body_generated": True,
        "preview": body[:500] + "..." if len(body) > 500 else body,
    }


@router.post(
    "/notifications/bulk-reminder",
    summary="Send reminders to multiple patients",
)
async def send_bulk_reminders(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Sends reminders to all patients with appointments tomorrow."""
    from sqlalchemy import text

    result = await db.execute(
        text(
            """
            SELECT c.id, c.start_datetime,
                   CONCAT(p.first_name, ' ', p.last_name) AS patient,
                   p.email,
                   CONCAT(m.first_name, ' ', m.last_name) AS doctor,
                   c.reason
            FROM appointments c
            JOIN patients p ON p.id = c.patient_id
            JOIN doctors m ON m.id = c.doctor_id
            JOIN appointment_statuses ec ON ec.id = c.status_id
            WHERE DATE(c.start_datetime) = DATE(NOW() + INTERVAL '1 day')
              AND ec.code IN ('PENDIENTE', 'CONFIRMADA')
            """
        )
    )
    appointments = result.mappings().all()

    sent = []
    for apt in appointments:
        subject, body = notification_service.generate_appointment_reminder(
            apt["patient"],
            apt["doctor"],
            str(apt["start_datetime"]),
        )
        sent.append(
            {
                "appointment_id": apt["id"],
                "patient": apt["patient"],
                "email": apt["email"],
                "subject": subject,
            }
        )

    return {
        "total_reminders": len(sent),
        "details": sent,
        "message": f"Generated {len(sent)} reminders for tomorrow.",
    }
