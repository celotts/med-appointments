from core.db import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class EstadoCita(Base):
    __tablename__ = "estados_cita"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(100), nullable=True)
