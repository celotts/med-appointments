from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from core.db import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .branch import Branch
    from .specialty import Specialty


class Doctor(Base):
    __tablename__ = "medicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    specialty_id: Mapped[int] = mapped_column(
        "especialidad_id", Integer, ForeignKey("especialidades.id", ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    first_name: Mapped[str] = mapped_column("nombre", String(100), nullable=False)
    last_name: Mapped[str] = mapped_column("apellido", String(100), nullable=False)
    professional_license: Mapped[str] = mapped_column(
        "cedula_profesional", String(50), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column("telefono", String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    specialty: Mapped[Specialty] = relationship(
        "Specialty", foreign_keys=[specialty_id]
    )
    branch: Mapped[Branch | None] = relationship("Branch", foreign_keys=[branch_id])
