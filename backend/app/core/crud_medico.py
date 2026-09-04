from models.medico import Medico as MedicoModel
from schemas.medico import MedicoCreate as MedicoCreateSchema
from schemas.medico import MedicoUpdate as MedicoUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_medico(db: AsyncSession, medico_id: int) -> MedicoModel | None:
    result = await db.execute(select(MedicoModel).filter(MedicoModel.id == medico_id))
    return result.scalars().first()


async def get_medicos(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[MedicoModel]:
    result = await db.execute(
        select(MedicoModel)
        .order_by(MedicoModel.apellido, MedicoModel.nombre)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_medicos_by_especialidad(
    db: AsyncSession, especialidad_id: int, skip: int = 0, limit: int = 100
) -> list[MedicoModel]:
    result = await db.execute(
        select(MedicoModel)
        .filter(MedicoModel.especialidad_id == especialidad_id)
        .order_by(MedicoModel.apellido)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def create_medico(db: AsyncSession, medico: MedicoCreateSchema) -> MedicoModel:
    db_medico = MedicoModel(**medico.model_dump())
    db.add(db_medico)
    await db.commit()
    await db.refresh(db_medico)
    return db_medico


async def update_medico(
    db: AsyncSession, db_medico: MedicoModel, medico: MedicoUpdateSchema
) -> MedicoModel:
    data = medico.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_medico, field, value)
    await db.commit()
    await db.refresh(db_medico)
    return db_medico


async def delete_medico(db: AsyncSession, medico_id: int) -> MedicoModel | None:
    result = await db.execute(select(MedicoModel).filter(MedicoModel.id == medico_id))
    db_medico = result.scalars().first()
    if db_medico:
        await db.delete(db_medico)
        await db.commit()
    return db_medico
