from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base


class Cita(Base):
    __tablename__ = "citas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paciente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pacientes.id", ondelete="RESTRICT"), nullable=False
    )
    medico_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medicos.id", ondelete="RESTRICT"), nullable=False
    )
    estado_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("estados_cita.id", ondelete="RESTRICT"), nullable=False
    )
    fecha_hora_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_hora_fin: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    motivo_consulta: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    paciente: Mapped["Paciente"] = relationship("Paciente")
    medico: Mapped["Medico"] = relationship("Medico")
    estado: Mapped["EstadoCita"] = relationship("EstadoCita")
