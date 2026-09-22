from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AppointmentStatusCode(str, Enum):
    """Possible status codes for a medical appointment.

    Values must match the Spanish codes stored in the DB (see
    script_BD/seeds/seed_catalogs.sql); the frontend and tests rely on them.
    """
    PENDING = "PENDIENTE"
    CONFIRMED = "CONFIRMADA"
    COMPLETED = "COMPLETADA"
    CANCELLED = "CANCELADA"
    SUSPENDED = "SUSPENDIDA"
    RESCHEDULED = "REAGENDADA"


# Valid transitions: WHERE you can go from a given state.
VALID_TRANSITIONS: dict[AppointmentStatusCode, set[AppointmentStatusCode]] = {
    AppointmentStatusCode.PENDING: {
        AppointmentStatusCode.CONFIRMED,
        AppointmentStatusCode.COMPLETED,
        AppointmentStatusCode.CANCELLED,
        AppointmentStatusCode.SUSPENDED,
        AppointmentStatusCode.RESCHEDULED,
    },
    AppointmentStatusCode.CONFIRMED: {
        AppointmentStatusCode.COMPLETED,
        AppointmentStatusCode.CANCELLED,
        AppointmentStatusCode.SUSPENDED,
        AppointmentStatusCode.RESCHEDULED,
    },
    AppointmentStatusCode.RESCHEDULED: {
        AppointmentStatusCode.CONFIRMED,
        AppointmentStatusCode.COMPLETED,
        AppointmentStatusCode.CANCELLED,
        AppointmentStatusCode.SUSPENDED,
    },
    AppointmentStatusCode.SUSPENDED: {
        AppointmentStatusCode.CONFIRMED,
        AppointmentStatusCode.COMPLETED,
        AppointmentStatusCode.RESCHEDULED,
    },
    AppointmentStatusCode.CANCELLED: set(),
    AppointmentStatusCode.COMPLETED: set(),
}


# --- Appointment statuses (catalog) ---
class AppointmentStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    description: str | None = None


# --- Visual indicator ---
class VisualIndicatorOut(BaseModel):
    code: str
    hex_color: str
    label: str


# --- Appointments ---
class AppointmentBase(BaseModel):
    patient_id: int
    doctor_id: int
    start_datetime: datetime
    end_datetime: datetime
    reason: str


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    reason: str | None = None


class AppointmentStatusUpdate(BaseModel):
    """Reschedule or transition status. `status` is required if using this path."""
    status: AppointmentStatusCode


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    status_id: int
    start_datetime: datetime
    end_datetime: datetime
    reason: str
    created_at: datetime | None = None
    status: AppointmentStatusOut | None = None
    
    # Campos visuales (nuevos)
    visual_indicator: Optional["VisualIndicatorOut"] = None
    is_delayed: Optional[bool] = None
    minutes_until: Optional[int] = None


# --- Medical notes ---
class MedicalNoteBase(BaseModel):
    diagnosis: str
    treatment: str | None = None
    observations: str | None = None


class MedicalNoteCreate(MedicalNoteBase):
    appointment_id: int


class MedicalNoteUpdate(BaseModel):
    diagnosis: str | None = None
    treatment: str | None = None
    observations: str | None = None


class MedicalNoteOut(MedicalNoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    created_at: datetime | None = None


# Resolve forward reference
VisualIndicatorOut.model_rebuild()
AppointmentOut.model_rebuild()


# --- Paginated response ---
class PaginatedResponse(BaseModel):
    items: list[AppointmentOut]
    total: int
    page: int
    page_size: int
    total_pages: int
