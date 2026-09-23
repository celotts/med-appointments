from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .medical_history import MedicalHistory

if TYPE_CHECKING:
    from .appointment import Appointment
    from .waitlist import Waitlist
    from .notification import Notification


def _get_appointment():
    from .appointment import Appointment
    return Appointment


def _get_waitlist():
    from .waitlist import Waitlist
    return Waitlist


def _get_notification():
    from .notification import Notification
    return Notification


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    document_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        _get_appointment, back_populates="patient"
    )
    waitlist_entries: Mapped[list["Waitlist"]] = relationship(
        _get_waitlist, back_populates="patient"
    )
    medical_histories: Mapped[list["MedicalHistory"]] = relationship(
        MedicalHistory, back_populates="patient"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        _get_notification, back_populates="patient"
    )
