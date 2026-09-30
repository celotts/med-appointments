from core import crud_medical_note_audit
from models.medical_note import MedicalNote as MedicalNoteModel
from models.user import User as UserModel
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
    db: AsyncSession,
    note: MedicalNoteCreateSchema,
    *,
    actor: UserModel | None = None,
) -> MedicalNoteModel:
    """Crea una nota clinica y la audita en la misma transaccion."""
    db_note = MedicalNoteModel(
        appointment_id=note.appointment_id,
        diagnosis=note.diagnosis,
        treatment=note.treatment,
        observations=note.observations,
    )
    db.add(db_note)
    await db.flush()  # necesitamos el id para el registro

    await crud_medical_note_audit.registrar_creacion(db, db_note, actor=actor)

    await db.commit()
    await db.refresh(db_note)
    return db_note


async def update_note(
    db: AsyncSession,
    db_note: MedicalNoteModel,
    note: MedicalNoteUpdateSchema,
    *,
    actor: UserModel | None = None,
) -> MedicalNoteModel:
    """Actualiza una nota clinica y audita antes/despues."""
    data = note.model_dump(exclude_unset=True)

    # Valores previos: sin ellos el registro solo diria "cambio la nota",
    # que no sirve para reconstruir que se corrigio.
    valores_previos = {
        campo: getattr(db_note, campo, None) for campo in data
    }
    for field, value in data.items():
        setattr(db_note, field, value)

    await crud_medical_note_audit.registrar_actualizacion(
        db,
        db_note,
        campos=data,
        valores_previos=valores_previos,
        actor=actor,
    )

    await db.commit()
    await db.refresh(db_note)
    return db_note


async def delete_note(
    db: AsyncSession, note_id: int, *, actor: UserModel | None = None
) -> MedicalNoteModel | None:
    """Elimina una nota clinica. El rastro se escribe antes del DELETE."""
    result = await db.execute(
        select(MedicalNoteModel).filter(MedicalNoteModel.id == note_id)
    )
    db_note = result.scalars().first()
    if db_note:
        await crud_medical_note_audit.registrar_borrado(db, db_note, actor=actor)
        await db.delete(db_note)
        await db.commit()
    return db_note
