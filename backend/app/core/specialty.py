from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class Specialty(Base):
    __tablename__ = "especialidades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    # created_at es manejado por la base de datos por defecto.
