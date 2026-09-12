from models.medical_history import MedicalHistory as MedicalHistoryModel
from schemas.medical_history import MedicalHistoryCreate as MedicalHistoryCreateSchema
from schemas.medical_history import MedicalHistoryUpdate as MedicalHistoryUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_medical_history(
    db: AsyncSession, history_id: str
) -> MedicalHistoryModel | None:
    result = await db.execute(
        select(MedicalHistoryModel).filter(MedicalHistoryModel.id == history_id)
    )
    return result.scalars().first()


async def get_medical_histories(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[MedicalHistoryModel]:
    result = await db.execute(select(MedicalHistoryModel).offset(skip).limit(limit))
    return result.scalars().all()


async def create_medical_history(
    db: AsyncSession, history: MedicalHistoryCreateSchema
) -> MedicalHistoryModel:
    db_history = MedicalHistoryModel(**history.model_dump())
    db.add(db_history)
    await db.commit()
    await db.refresh(db_history)
    return db_history


async def update_medical_history(
    db: AsyncSession,
    db_history: MedicalHistoryModel,
    history: MedicalHistoryUpdateSchema,
) -> MedicalHistoryModel:
    data = history.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_history, field, value)
    await db.commit()
    await db.refresh(db_history)
    return db_history


async def delete_medical_history(
    db: AsyncSession, history_id: str
) -> MedicalHistoryModel | None:
    result = await db.execute(
        select(MedicalHistoryModel).filter(MedicalHistoryModel.id == history_id)
    )
    db_history = result.scalars().first()
    if db_history:
        await db.delete(db_history)
        await db.commit()
    return db_history
