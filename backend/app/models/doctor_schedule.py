from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Time, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from .doctor import Doctor


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    doctor = relationship("Doctor", back_populates="schedules", foreign_keys=[doctor_id])

    def __repr__(self) -> str:
        return f"DoctorSchedule(id={self.id}, doctor_id={self.doctor_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})"
