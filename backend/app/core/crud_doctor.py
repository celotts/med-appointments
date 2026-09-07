from models.doctor import Doctor as DoctorModel
from schemas.doctor import DoctorCreate as DoctorCreateSchema
from schemas.doctor import DoctorUpdate as DoctorUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_doctor(db: AsyncSession, doctor_id: int) -> DoctorModel | None:
    result = await db.execute(select(DoctorModel).filter(DoctorModel.id == doctor_id))
    return result.scalars().first()


async def get_doctors(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[DoctorModel]:
    result = await db.execute(
        select(DoctorModel)
        .order_by(DoctorModel.last_name, DoctorModel.first_name)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_doctors_by_specialty(
    db: AsyncSession, specialty_id: int, skip: int = 0, limit: int = 100
) -> list[DoctorModel]:
    result = await db.execute(
        select(DoctorModel)
        .filter(DoctorModel.specialty_id == specialty_id)
        .order_by(DoctorModel.last_name)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def create_doctor(db: AsyncSession, doctor: DoctorCreateSchema) -> DoctorModel:
    db_doctor = DoctorModel(**doctor.model_dump())
    db.add(db_doctor)
    await db.commit()
    await db.refresh(db_doctor)
    return db_doctor


async def update_doctor(
    db: AsyncSession, db_doctor: DoctorModel, doctor: DoctorUpdateSchema
) -> DoctorModel:
    data = doctor.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_doctor, field, value)
    await db.commit()
    await db.refresh(db_doctor)
    return db_doctor


async def delete_doctor(db: AsyncSession, doctor_id: int) -> DoctorModel | None:
    result = await db.execute(select(DoctorModel).filter(DoctorModel.id == doctor_id))
    db_doctor = result.scalars().first()
    if db_doctor:
        await db.delete(db_doctor)
        await db.commit()
    return db_doctor
