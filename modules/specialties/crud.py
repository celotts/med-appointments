from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.specialty import Specialty
from .schemas import SpecialtyCreate, SpecialtyUpdate


async def get_specialty(db: AsyncSession, specialty_id: int) -> Optional[Specialty]:
    result = await db.execute(select(Specialty).where(Specialty.id == specialty_id))
    return result.scalar_one_or_none()


async def get_specialties(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Specialty]:
    result = await db.execute(select(Specialty).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_specialty(db: AsyncSession, specialty_in: SpecialtyCreate) -> Specialty:
    db_specialty = Specialty(name=specialty_in.name, description=specialty_in.description)
    db.add(db_specialty)
    await db.commit()
    await db.refresh(db_specialty)
    return db_specialty


async def update_specialty(db: AsyncSession, specialty_id: int, specialty_in: SpecialtyUpdate) -> Optional[Specialty]:
    db_specialty = await get_specialty(db, specialty_id)
    if not db_specialty:
        return None
    update_data = specialty_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_specialty, field, value)
    await db.commit()
    await db.refresh(db_specialty)
    return db_specialty


async def delete_specialty(db: AsyncSession, specialty_id: int) -> bool:
    db_specialty = await get_specialty(db, specialty_id)
    if not db_specialty:
        return False
    await db.delete(db_specialty)
    await db.commit()
    return True
