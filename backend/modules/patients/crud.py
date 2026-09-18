from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.patient import Patient
from .schemas import PatientCreate, PatientUpdate


async def get_patient(db: AsyncSession, patient_id: int) -> Optional[Patient]:
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    return result.scalar_one_or_none()


async def get_patients(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Patient]:
    result = await db.execute(select(Patient).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_patient(db: AsyncSession, patient_in: PatientCreate) -> Patient:
    db_patient = Patient(
        first_name=patient_in.first_name,
        last_name=patient_in.last_name,
        birth_date=patient_in.birth_date,
        email=patient_in.email,
        phone=patient_in.phone,
    )
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)
    return db_patient


async def update_patient(db: AsyncSession, patient_id: int, patient_in: PatientUpdate) -> Optional[Patient]:
    db_patient = await get_patient(db, patient_id)
    if not db_patient:
        return None
    update_data = patient_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_patient, field, value)
    await db.commit()
    await db.refresh(db_patient)
    return db_patient


async def delete_patient(db: AsyncSession, patient_id: int) -> bool:
    db_patient = await get_patient(db, patient_id)
    if not db_patient:
        return False
    await db.delete(db_patient)
    await db.commit()
    return True
