from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.doctor import Doctor
from .schemas import DoctorCreate, DoctorUpdate


async def get_doctor(db: AsyncSession, doctor_id: int) -> Optional[Doctor]:
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    return result.scalar_one_or_none()


async def get_doctors(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Doctor]:
    result = await db.execute(select(Doctor).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_doctor(db: AsyncSession, doctor_in: DoctorCreate) -> Doctor:
    db_doctor = Doctor(
        specialty_id=doctor_in.specialty_id,
        branch_id=doctor_in.branch_id,
        first_name=doctor_in.first_name,
        last_name=doctor_in.last_name,
        professional_license=doctor_in.professional_license,
        email=doctor_in.email,
        phone=doctor_in.phone,
    )
    db.add(db_doctor)
    await db.commit()
    await db.refresh(db_doctor)
    return db_doctor


async def update_doctor(db: AsyncSession, doctor_id: int, doctor_in: DoctorUpdate) -> Optional[Doctor]:
    db_doctor = await get_doctor(db, doctor_id)
    if not db_doctor:
        return None
    update_data = doctor_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_doctor, field, value)
    await db.commit()
    await db.refresh(db_doctor)
    return db_doctor


async def delete_doctor(db: AsyncSession, doctor_id: int) -> bool:
    db_doctor = await get_doctor(db, doctor_id)
    if not db_doctor:
        return False
    await db.delete(db_doctor)
    await db.commit()
    return True
