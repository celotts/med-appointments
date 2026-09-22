from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from .medical_history import MedicalHistory


class ConsultingRoom(Base):
    __tablename__ = "consulting_rooms"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(15), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    medical_histories: Mapped[list["MedicalHistory"]] = relationship(
        "MedicalHistory", back_populates="consulting_room"
    )

    def __repr__(self):
        return f"ConsultingRoom(id={self.id}, name={self.name})"
