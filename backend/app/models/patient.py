from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from core.db import Base
from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .appointment import Appointment
    from .waitlist import Waitlist


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", back_populates="patient"
    )
    waitlist_entries: Mapped[list[Waitlist]] = relationship(
        "Waitlist", back_populates="patient"
    )
