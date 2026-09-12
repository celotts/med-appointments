from models.doctor_schedule import DoctorSchedule as DoctorScheduleModel
from schemas.doctor_schedule import DoctorScheduleCreate as DoctorScheduleCreateSchema
from schemas.doctor_schedule import DoctorScheduleUpdate as DoctorScheduleUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_doctor_schedule(
    db: AsyncSession, schedule_id: str
) -> DoctorScheduleModel | None:
    result = await db.execute(
        select(DoctorScheduleModel).filter(DoctorScheduleModel.id == schedule_id)
    )
    return result.scalars().first()


async def get_doctor_schedules(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[DoctorScheduleModel]:
    result = await db.execute(select(DoctorScheduleModel).offset(skip).limit(limit))
    return result.scalars().all()


async def create_doctor_schedule(
    db: AsyncSession, schedule: DoctorScheduleCreateSchema
) -> DoctorScheduleModel:
    db_schedule = DoctorScheduleModel(**schedule.model_dump())
    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)
    return db_schedule


async def update_doctor_schedule(
    db: AsyncSession,
    db_schedule: DoctorScheduleModel,
    schedule: DoctorScheduleUpdateSchema,
) -> DoctorScheduleModel:
    data = schedule.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_schedule, field, value)
    await db.commit()
    await db.refresh(db_schedule)
    return db_schedule


async def delete_doctor_schedule(
    db: AsyncSession, schedule_id: str
) -> DoctorScheduleModel | None:
    result = await db.execute(
        select(DoctorScheduleModel).filter(DoctorScheduleModel.id == schedule_id)
    )
    db_schedule = result.scalars().first()
    if db_schedule:
        await db.delete(db_schedule)
        await db.commit()
    return db_schedule
