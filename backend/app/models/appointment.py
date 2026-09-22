from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .user import User

if TYPE_CHECKING:
    from .doctor import Doctor
    from .patient import Patient
    from .appointment_status import AppointmentStatus
    from .medical_note import MedicalNote


def _get_doctor():
    from .doctor import Doctor
    return Doctor

def _get_patient():
    from .patient import Patient
    return Patient

def _get_appointment_status():
    from .appointment_status import AppointmentStatus
    return AppointmentStatus

def _get_medical_note():
    from .medical_note import MedicalNote
    return MedicalNote


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey(User.id, ondelete="CASCADE"), nullable=False
    )
    status_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("appointment_statuses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    patient: Mapped["Patient"] = relationship(
        _get_patient, back_populates="appointments", foreign_keys=[patient_id]
    )
    doctor: Mapped["Doctor"] = relationship(_get_doctor, foreign_keys=[doctor_id])
    user: Mapped["User"] = relationship(User, foreign_keys=[user_id])
    status: Mapped["AppointmentStatus"] = relationship(
        _get_appointment_status, back_populates="appointments", foreign_keys=[status_id]
    )
    medical_note: Mapped["MedicalNote"] = relationship(
        _get_medical_note, back_populates="appointment", uselist=False
    )
