from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .specialty import Specialty
from .branch import Branch


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    specialty_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(Specialty.id, ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(Branch.id, ondelete="SET NULL"), nullable=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    document_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    professional_license: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )

    specialty: Mapped["Specialty"] = relationship(
        Specialty, foreign_keys=[specialty_id]
    )
    branch: Mapped["Branch | None"] = relationship(Branch, foreign_keys=[branch_id])
    # `passive_deletes=True` delega en la BD. Sin esto, SQLAlchemy emitia un
    # UPDATE poniendole NULL a la FK hija, que en columnas NOT NULL hacia
    # fallar el DELETE. El esquema define ON DELETE CASCADE para doctor_schedules
    # y ON DELETE RESTRICT para medical_histories. Ver app/models/patient.py.
    schedules: Mapped[list["DoctorSchedule"]] = relationship(
        "DoctorSchedule", back_populates="doctor", passive_deletes=True
    )
    medical_histories: Mapped[list["MedicalHistory"]] = relationship(
        "MedicalHistory", back_populates="doctor", passive_deletes=True
    )
    
