from core.db import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class AppointmentStatus(Base):
    __tablename__ = "appointment_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(100), nullable=True)
