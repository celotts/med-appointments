from models.patient import Patient as PatientModel
from schemas.patient import PatientCreate as PatientCreateSchema
from schemas.patient import PatientUpdate as PatientUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_patient(db: AsyncSession, patient_id: int) -> PatientModel | None:
    result = await db.execute(
        select(PatientModel).filter(PatientModel.id == patient_id)
    )
    return result.scalars().first()


async def get_patients(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[PatientModel]:
    result = await db.execute(
        select(PatientModel)
        .order_by(PatientModel.last_name, PatientModel.first_name)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def create_patient(
    db: AsyncSession, patient: PatientCreateSchema
) -> PatientModel:
    db_patient = PatientModel(**patient.model_dump())
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)
    return db_patient


async def update_patient(
    db: AsyncSession, db_patient: PatientModel, patient: PatientUpdateSchema
) -> PatientModel:
    data = patient.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_patient, field, value)
    await db.commit()
    await db.refresh(db_patient)
    return db_patient


async def delete_patient(db: AsyncSession, patient_id: int) -> PatientModel | None:
    result = await db.execute(
        select(PatientModel).filter(PatientModel.id == patient_id)
    )
    db_patient = result.scalars().first()
    if db_patient:
        await db.delete(db_patient)
        await db.commit()
    return db_patient
