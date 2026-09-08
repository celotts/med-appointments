from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from core.db import Base
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .doctor import Doctor
    from .patient import Patient


class Waitlist(Base):
    __tablename__ = "waitlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        "paciente_id", Integer, ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False
    )
    doctor_id: Mapped[int] = mapped_column(
        "medico_id", Integer, ForeignKey("medicos.id", ondelete="CASCADE"), nullable=False
    )
    preferred_date: Mapped[date] = mapped_column("fecha_preferida", Date, nullable=False)
    reason: Mapped[str | None] = mapped_column("motivo", Text, nullable=True)
    status: Mapped[str] = mapped_column("estado", String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    patient: Mapped[Patient] = relationship("Patient", foreign_keys=[patient_id])
    doctor: Mapped[Doctor] = relationship("Doctor", foreign_keys=[doctor_id])
