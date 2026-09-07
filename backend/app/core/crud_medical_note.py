from models.medical_note import MedicalNote as MedicalNoteModel
from schemas.appointment import (
    MedicalNoteCreate as MedicalNoteCreateSchema,
)
from schemas.appointment import (
    MedicalNoteUpdate as MedicalNoteUpdateSchema,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_note(db: AsyncSession, note_id: int) -> MedicalNoteModel | None:
    result = await db.execute(
        select(MedicalNoteModel).filter(MedicalNoteModel.id == note_id)
    )
    return result.scalars().first()


async def get_note_by_appointment(db: AsyncSession, appointment_id: int) -> MedicalNoteModel | None:
    result = await db.execute(
        select(MedicalNoteModel).filter(MedicalNoteModel.appointment_id == appointment_id)
    )
    return result.scalars().first()


async def get_notes(
    db: AsyncSession, skip: int = 0, limit: int = 100, appointment_id: int | None = None
) -> list[MedicalNoteModel]:
    stmt = select(MedicalNoteModel).order_by(MedicalNoteModel.created_at.desc())
    if appointment_id is not None:
        stmt = stmt.where(MedicalNoteModel.appointment_id == appointment_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_note(
    db: AsyncSession, note: MedicalNoteCreateSchema
) -> MedicalNoteModel:
    db_note = MedicalNoteModel(
        appointment_id=note.appointment_id,
        diagnosis=note.diagnosis,
        treatment=note.treatment,
        observations=note.observations,
    )
    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)
    return db_note


async def update_note(
    db: AsyncSession, db_note: MedicalNoteModel, note: MedicalNoteUpdateSchema
) -> MedicalNoteModel:
    data = note.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_note, field, value)
    await db.commit()
    await db.refresh(db_note)
    return db_note


async def delete_note(db: AsyncSession, note_id: int) -> MedicalNoteModel | None:
    result = await db.execute(
        select(MedicalNoteModel).filter(MedicalNoteModel.id == note_id)
    )
    db_note = result.scalars().first()
    if db_note:
        await db.delete(db_note)
        await db.commit()
    return db_note
