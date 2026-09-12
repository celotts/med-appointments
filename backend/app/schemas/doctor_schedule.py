from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, Field, TypeAdapter
from schemas import BaseSchema as BaseSchema


class DoctorScheduleBase(BaseModel):
    doctor_id: str = Field(..., description="ID del médico (UUID)")
    day_of_week: int = Field(
        ..., ge=1, le=7, description="Día de la semana (1=Lunes, 7=Domingo)"
    )
    start_time: time = Field(..., description="Hora de inicio")
    end_time: time = Field(..., description="Hora de fin")
    slot_duration_minutes: int = Field(
        default=30, ge=1, le=120, description="Duración de la cita en minutos"
    )


class DoctorScheduleCreate(DoctorScheduleBase):
    pass


class DoctorScheduleUpdate(BaseModel):
    doctor_id: str | None = Field(default=None, description="ID del médico (UUID)")
    day_of_week: int | None = Field(
        default=None, ge=1, le=7, description="Día de la semana (1=Lunes, 7=Domingo)"
    )
    start_time: time | None = Field(default=None, description="Hora de inicio")
    end_time: time | None = Field(default=None, description="Hora de fin")
    slot_duration_minutes: int | None = Field(
        default=None, ge=1, le=120, description="Duración de la cita en minutos"
    )


class DoctorScheduleResponse(DoctorScheduleBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Helper to convert time to string for frontend
def time_to_str(t: time) -> str:
    return t.strftime("%H:%M") if t else ""


# TypeAdapter for serialization
DoctorScheduleTimeAdapter = TypeAdapter(time)
