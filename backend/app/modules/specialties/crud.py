from __future__ import annotations

from models.specialty import Specialty
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .schemas import SpecialtyCreate


async def get_specialty(db: AsyncSession, specialty_id: int) -> Specialty | None:
    result = await db.execute(select(Specialty).where(Specialty.id == specialty_id))
    return result.scalar_one_or_none()


async def get_specialties(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Specialty]:
    result = await db.execute(select(Specialty).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_specialty(
    db: AsyncSession, specialty_in: SpecialtyCreate
) -> Specialty:
    db_specialty = Specialty(
        name=specialty_in.name, description=specialty_in.description
    )
    db.add(db_specialty)
    await db.commit()
    await db.refresh(db_specialty)
    return db_specialty
