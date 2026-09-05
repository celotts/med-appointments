from datetime import datetime

from core.db import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Medico(Base):
    __tablename__ = "medicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    especialidad_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("especialidades.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    cedula_profesional: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    especialidad: Mapped["Specialty"] = relationship(
        "Specialty", foreign_keys=[especialidad_id]
    )
