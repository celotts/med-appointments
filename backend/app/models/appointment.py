from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from core.db import Base
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .appointment_status import AppointmentStatus
    from .doctor import Doctor
    from .patient import Patient


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("appointment_statuses.id", ondelete="RESTRICT"), nullable=False
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

    patient: Mapped[Patient] = relationship("Patient")
    doctor: Mapped[Doctor] = relationship("Doctor")
    status: Mapped[AppointmentStatus] = relationship("AppointmentStatus")
