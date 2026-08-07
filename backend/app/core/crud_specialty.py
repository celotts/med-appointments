from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.specialty import Specialty as SpecialtyModel
from schemas.specialty import SpecialtyCreate as SpecialtyCreateSchema


async def get_specialties(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[SpecialtyModel]:
    result = await db.execute(select(SpecialtyModel).offset(skip).limit(limit))
    return result.scalars().all()


async def create_specialty(
    db: AsyncSession, specialty: SpecialtyCreateSchema
) -> SpecialtyModel:
    db_specialty = SpecialtyModel(
        nombre=specialty.nombre, descripcion=specialty.descripcion
    )
    db.add(db_specialty)
    await db.commit()
    await db.refresh(db_specialty)
    return db_specialty
