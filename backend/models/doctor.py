from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from core.db import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .specialty import Specialty
    from .branch import Branch


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    specialty_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("specialties.id", ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    professional_license: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    specialty: Mapped[Specialty] = relationship(
        "Specialty", foreign_keys=[specialty_id]
    )
    branch: Mapped[Optional[Branch]] = relationship(
        "Branch", foreign_keys=[branch_id]
    )
