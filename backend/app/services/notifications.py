"""Notification system for medical appointments."""

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from core.config import settings


class NotificationService:
    """Central notification service."""

    def __init__(self):
        self.email_enabled = hasattr(settings, "SMTP_HOST") and settings.SMTP_HOST

    async def send_email(
        self, to: str, subject: str, body: str, html: bool = True
    ) -> dict[str, Any]:
        """Sends a notification email."""
        if not self.email_enabled:
            return {
                "status": "simulated",
                "to": to,
                "subject": subject,
                "message": "Email not configured (SMTP unavailable)",
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = settings.SMTP_FROM or "noreply@medappointments.com"
            msg["To"] = to
            msg["Subject"] = subject

            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT or 587) as server:
                server.starttls()
                if hasattr(settings, "SMTP_USER") and settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
                server.send_message(msg)

            return {"status": "sent", "to": to, "subject": subject}
        except Exception as exc:
            return {"status": "error", "to": to, "error": str(exc)}

    def generate_appointment_confirmation(
        self, patient: str, doctor: str, date: str, reason: str
    ) -> tuple[str, str]:
        """Generates appointment confirmation email."""
        subject = f"Appointment Confirmation - {date}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #2563eb;">Appointment Confirmation</h2>
            <p>Dear <strong>{patient}</strong>,</p>
            <p>Your appointment has been successfully scheduled:</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px;">
                <p><strong>Doctor:</strong> {doctor}</p>
                <p><strong>Date:</strong> {date}</p>
                <p><strong>Reason:</strong> {reason}</p>
            </div>
            <p>Please arrive 10 minutes before your appointment.</p>
            <p>If you need to cancel or reschedule, please do so 24 hours in advance.</p>
            <hr>
            <p style="color: #6b7280; font-size: 12px;">MedAppointments - Appointment Management System</p>
        </body>
        </html>
        """
        return subject, body

    def generate_appointment_reminder(
        self, patient: str, doctor: str, date: str, hours: int = 24
    ) -> tuple[str, str]:
        """Generates reminder email."""
        subject = f"Reminder: Your appointment is in {hours} hours"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #f59e0b;">Appointment Reminder</h2>
            <p>Dear <strong>{patient}</strong>,</p>
            <p>This is a reminder that you have an upcoming appointment:</p>
            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <p><strong>Doctor:</strong> {doctor}</p>
                <p><strong>Date:</strong> {date}</p>
            </div>
            <p>Please confirm your attendance or cancel in advance.</p>
            <hr>
            <p style="color: #6b7280; font-size: 12px;">MedAppointments - Appointment Management System</p>
        </body>
        </html>
        """
        return subject, body

    def generate_cancellation_notice(
        self, patient: str, doctor: str, date: str, reason: str
    ) -> tuple[str, str]:
        """Generates cancellation email."""
        subject = f"Appointment Cancelled - {date}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #ef4444;">Appointment Cancelled</h2>
            <p>Dear <strong>{patient}</strong>,</p>
            <p>Your appointment has been cancelled:</p>
            <div style="background: #fee2e2; padding: 15px; border-radius: 8px; border-left: 4px solid #ef4444;">
                <p><strong>Doctor:</strong> {doctor}</p>
                <p><strong>Date:</strong> {date}</p>
                <p><strong>Reason:</strong> {reason}</p>
            </div>
            <p>If you would like to reschedule, please contact us.</p>
            <hr>
            <p style="color: #6b7280; font-size: 12px;">MedAppointments - Appointment Management System</p>
        </body>
        </html>
        """
        return subject, body

    def generate_reschedule_notice(
        self,
        patient: str,
        doctor: str,
        previous_date: str,
        new_date: str,
    ) -> tuple[str, str]:
        """Generates reschedule email."""
        subject = f"Appointment Rescheduled - New Date: {new_date}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #8b5cf6;">Appointment Rescheduled</h2>
            <p>Dear <strong>{patient}</strong>,</p>
            <p>Your appointment has been rescheduled:</p>
            <div style="background: #ede9fe; padding: 15px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
                <p><strong>Doctor:</strong> {doctor}</p>
                <p><strong>Previous date:</strong> {previous_date}</p>
                <p><strong>New date:</strong> {new_date}</p>
            </div>
            <p>We apologize for any inconvenience.</p>
            <hr>
            <p style="color: #6b7280; font-size: 12px;">MedAppointments - Appointment Management System</p>
        </body>
        </html>
        """
        return subject, body


notification_service = NotificationService()
