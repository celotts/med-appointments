from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.appointment_status import AppointmentStatus
from .schemas import AppointmentStatusCreate, AppointmentStatusUpdate


async def get_appointment_status(db: AsyncSession, status_id: int) -> Optional[AppointmentStatus]:
    result = await db.execute(select(AppointmentStatus).where(AppointmentStatus.id == status_id))
    return result.scalar_one_or_none()


async def get_appointment_statuses(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[AppointmentStatus]:
    result = await db.execute(select(AppointmentStatus).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_appointment_status(db: AsyncSession, status_in: AppointmentStatusCreate) -> AppointmentStatus:
    db_status = AppointmentStatus(
        code=status_in.code,
        description=status_in.description,
    )
    db.add(db_status)
    await db.commit()
    await db.refresh(db_status)
    return db_status


async def update_appointment_status(db: AsyncSession, status_id: int, status_in: AppointmentStatusUpdate) -> Optional[AppointmentStatus]:
    db_status = await get_appointment_status(db, status_id)
    if not db_status:
        return None
    update_data = status_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_status, field, value)
    await db.commit()
    await db.refresh(db_status)
    return db_status


async def delete_appointment_status(db: AsyncSession, status_id: int) -> bool:
    db_status = await get_appointment_status(db, status_id)
    if not db_status:
        return False
    await db.delete(db_status)
    await db.commit()
    return True
