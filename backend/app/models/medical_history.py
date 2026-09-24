from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .consulting_room import ConsultingRoom

if TYPE_CHECKING:
    pass


class MedicalHistory(Base):
    __tablename__ = "medical_histories"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False)
    consulting_room_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("consulting_rooms.id"), nullable=True
    )
    diagnosis: Mapped[str | None] = mapped_column(String, nullable=True)
    prescription: Mapped[str | None] = mapped_column(String, nullable=True)
    treatment: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    patient = relationship("Patient", back_populates="medical_histories")
    doctor = relationship("Doctor", back_populates="medical_histories")
    consulting_room = relationship(ConsultingRoom, back_populates="medical_histories")

    def __repr__(self) -> str:
        return f"MedicalHistory(id={self.id}, patient_id={self.patient_id}, date={self.date})"
