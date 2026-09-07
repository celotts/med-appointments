from models.specialty import Specialty as SpecialtyModel
from schemas.specialty import SpecialtyCreate as SpecialtyCreateSchema
from schemas.specialty import SpecialtyUpdate as SpecialtyUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_specialty(db: AsyncSession, specialty_id: int) -> SpecialtyModel | None:
    result = await db.execute(
        select(SpecialtyModel).filter(SpecialtyModel.id == specialty_id)
    )
    return result.scalars().first()


async def get_specialties(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[SpecialtyModel]:
    result = await db.execute(
        select(SpecialtyModel).order_by(SpecialtyModel.name).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def create_specialty(
    db: AsyncSession, specialty: SpecialtyCreateSchema
) -> SpecialtyModel:
    db_specialty = SpecialtyModel(
        name=specialty.name, description=specialty.description
    )
    db.add(db_specialty)
    await db.commit()
    await db.refresh(db_specialty)
    return db_specialty


async def update_specialty(
    db: AsyncSession,
    db_specialty: SpecialtyModel,
    specialty: SpecialtyUpdateSchema,
) -> SpecialtyModel:
    data = specialty.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_specialty, field, value)
    await db.commit()
    await db.refresh(db_specialty)
    return db_specialty


async def delete_specialty(
    db: AsyncSession, specialty_id: int
) -> SpecialtyModel | None:
    result = await db.execute(
        select(SpecialtyModel).filter(SpecialtyModel.id == specialty_id)
    )
    db_specialty = result.scalars().first()
    if db_specialty:
        await db.delete(db_specialty)
        await db.commit()
    return db_specialty
