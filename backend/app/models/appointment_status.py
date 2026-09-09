from __future__ import annotations

from typing import TYPE_CHECKING

from core.db import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .appointment import Appointment


class AppointmentStatus(Base):
    __tablename__ = "appointment_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(100), nullable=True)

    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", back_populates="status"
    )
