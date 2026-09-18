from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.appointment import Appointment
from .schemas import AppointmentCreate, AppointmentUpdate


async def get_appointment(db: AsyncSession, appointment_id: int) -> Optional[Appointment]:
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    return result.scalar_one_or_none()


async def get_appointments(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Appointment]:
    result = await db.execute(select(Appointment).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_appointment(db: AsyncSession, appointment_in: AppointmentCreate) -> Appointment:
    db_appointment = Appointment(
        patient_id=appointment_in.patient_id,
        doctor_id=appointment_in.doctor_id,
        status_id=appointment_in.status_id,
        start_datetime=appointment_in.start_datetime,
        end_datetime=appointment_in.end_datetime,
        reason=appointment_in.reason,
    )
    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)
    return db_appointment


async def update_appointment(db: AsyncSession, appointment_id: int, appointment_in: AppointmentUpdate) -> Optional[Appointment]:
    db_appointment = await get_appointment(db, appointment_id)
    if not db_appointment:
        return None
    update_data = appointment_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_appointment, field, value)
    await db.commit()
    await db.refresh(db_appointment)
    return db_appointment


async def delete_appointment(db: AsyncSession, appointment_id: int) -> bool:
    db_appointment = await get_appointment(db, appointment_id)
    if not db_appointment:
        return False
    await db.delete(db_appointment)
    await db.commit()
    return True
