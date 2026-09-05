from datetime import datetime

from core.db import Base
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class NotaMedica(Base):
    __tablename__ = "notas_medicas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cita_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("citas.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    diagnostico: Mapped[str] = mapped_column(Text, nullable=False)
    tratamiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )
