from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.medical_note import MedicalNote
from .schemas import MedicalNoteCreate, MedicalNoteUpdate


async def get_medical_note(db: AsyncSession, note_id: int) -> Optional[MedicalNote]:
    result = await db.execute(select(MedicalNote).where(MedicalNote.id == note_id))
    return result.scalar_one_or_none()


async def get_medical_notes(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[MedicalNote]:
    result = await db.execute(select(MedicalNote).offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_medical_note_by_appointment(db: AsyncSession, appointment_id: int) -> Optional[MedicalNote]:
    result = await db.execute(select(MedicalNote).where(MedicalNote.appointment_id == appointment_id))
    return result.scalar_one_or_none()


async def create_medical_note(db: AsyncSession, note_in: MedicalNoteCreate) -> MedicalNote:
    db_note = MedicalNote(
        appointment_id=note_in.appointment_id,
        diagnosis=note_in.diagnosis,
        treatment=note_in.treatment,
        observations=note_in.observations,
    )
    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)
    return db_note


async def update_medical_note(db: AsyncSession, note_id: int, note_in: MedicalNoteUpdate) -> Optional[MedicalNote]:
    db_note = await get_medical_note(db, note_id)
    if not db_note:
        return None
    update_data = note_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_note, field, value)
    await db.commit()
    await db.refresh(db_note)
    return db_note


async def delete_medical_note(db: AsyncSession, note_id: int) -> bool:
    db_note = await get_medical_note(db, note_id)
    if not db_note:
        return False
    await db.delete(db_note)
    await db.commit()
    return True
