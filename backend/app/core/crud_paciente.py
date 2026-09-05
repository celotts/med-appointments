from models.paciente import Paciente as PacienteModel
from schemas.paciente import PacienteCreate as PacienteCreateSchema
from schemas.paciente import PacienteUpdate as PacienteUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_paciente(db: AsyncSession, paciente_id: int) -> PacienteModel | None:
    result = await db.execute(
        select(PacienteModel).filter(PacienteModel.id == paciente_id)
    )
    return result.scalars().first()


async def get_pacientes(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[PacienteModel]:
    result = await db.execute(
        select(PacienteModel)
        .order_by(PacienteModel.apellido, PacienteModel.nombre)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def create_paciente(
    db: AsyncSession, paciente: PacienteCreateSchema
) -> PacienteModel:
    db_paciente = PacienteModel(**paciente.model_dump())
    db.add(db_paciente)
    await db.commit()
    await db.refresh(db_paciente)
    return db_paciente


async def update_paciente(
    db: AsyncSession, db_paciente: PacienteModel, paciente: PacienteUpdateSchema
) -> PacienteModel:
    data = paciente.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_paciente, field, value)
    await db.commit()
    await db.refresh(db_paciente)
    return db_paciente


async def delete_paciente(db: AsyncSession, paciente_id: int) -> PacienteModel | None:
    result = await db.execute(
        select(PacienteModel).filter(PacienteModel.id == paciente_id)
    )
    db_paciente = result.scalars().first()
    if db_paciente:
        await db.delete(db_paciente)
        await db.commit()
    return db_paciente
