from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.nota_medica import NotaMedica as NotaMedicaModel
from schemas.cita import (
    NotaMedicaCreate as NotaMedicaCreateSchema,
    NotaMedicaUpdate as NotaMedicaUpdateSchema,
)


async def get_nota(db: AsyncSession, nota_id: int) -> NotaMedicaModel | None:
    result = await db.execute(
        select(NotaMedicaModel).filter(NotaMedicaModel.id == nota_id)
    )
    return result.scalars().first()


async def get_nota_by_cita(db: AsyncSession, cita_id: int) -> NotaMedicaModel | None:
    result = await db.execute(
        select(NotaMedicaModel).filter(NotaMedicaModel.cita_id == cita_id)
    )
    return result.scalars().first()


async def get_notas(
    db: AsyncSession, skip: int = 0, limit: int = 100, cita_id: int | None = None
) -> list[NotaMedicaModel]:
    stmt = select(NotaMedicaModel).order_by(NotaMedicaModel.created_at.desc())
    if cita_id is not None:
        stmt = stmt.where(NotaMedicaModel.cita_id == cita_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_nota(
    db: AsyncSession, nota: NotaMedicaCreateSchema
) -> NotaMedicaModel:
    db_nota = NotaMedicaModel(
        cita_id=nota.cita_id,
        diagnostico=nota.diagnostico,
        tratamiento=nota.tratamiento,
        observaciones=nota.observaciones,
    )
    db.add(db_nota)
    await db.commit()
    await db.refresh(db_nota)
    return db_nota


async def update_nota(
    db: AsyncSession, db_nota: NotaMedicaModel, nota: NotaMedicaUpdateSchema
) -> NotaMedicaModel:
    data = nota.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_nota, field, value)
    await db.commit()
    await db.refresh(db_nota)
    return db_nota


async def delete_nota(db: AsyncSession, nota_id: int) -> NotaMedicaModel | None:
    result = await db.execute(
        select(NotaMedicaModel).filter(NotaMedicaModel.id == nota_id)
    )
    db_nota = result.scalars().first()
    if db_nota:
        await db.delete(db_nota)
        await db.commit()
    return db_nota
