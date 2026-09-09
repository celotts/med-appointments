from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from core.db import Base
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .appointment import Appointment


class MedicalNote(Base):
    __tablename__ = "medical_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("appointments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    treatment: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    appointment: Mapped[Appointment] = relationship(
        "Appointment", back_populates="medical_note", foreign_keys=[appointment_id]
    )
