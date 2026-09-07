from datetime import datetime

from core.db import Base
from sqlalchemy import Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(), nullable=False
    )
