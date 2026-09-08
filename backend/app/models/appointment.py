from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from core.db import Base
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .appointment_status import AppointmentStatus
    from .doctor import Doctor
    from .medical_note import MedicalNote
    from .patient import Patient


class Appointment(Base):
    __tablename__ = "citas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        "paciente_id", Integer, ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[int] = mapped_column(
        "medico_id", Integer, ForeignKey("medicos.id", ondelete="RESTRICT"), nullable=False
    )
    status_id: Mapped[int] = mapped_column(
        "estado_id", Integer,
        ForeignKey("estados_cita.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_datetime: Mapped[datetime] = mapped_column(
        "fecha_hora_inicio", DateTime(timezone=True), nullable=False
    )
    end_datetime: Mapped[datetime] = mapped_column(
        "fecha_hora_fin", DateTime(timezone=True), nullable=False
    )
    reason: Mapped[str] = mapped_column("motivo_consulta", Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    patient: Mapped[Patient] = relationship(
        "Patient", back_populates="appointments", foreign_keys=[patient_id]
    )
    doctor: Mapped[Doctor] = relationship("Doctor", foreign_keys=[doctor_id])
    status: Mapped[AppointmentStatus] = relationship(
        "AppointmentStatus", back_populates="appointments", foreign_keys=[status_id]
    )
    medical_note: Mapped[MedicalNote | None] = relationship(
        "MedicalNote", back_populates="appointment", uselist=False
    )
