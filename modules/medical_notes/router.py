from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import MedicalNoteCreate, MedicalNoteUpdate, MedicalNoteResponse
from . import crud

router = APIRouter(prefix="/medical-notes", tags=["Medical Notes"])


@router.get("/", response_model=List[MedicalNoteResponse])
async def read_medical_notes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_medical_notes(db, skip=skip, limit=limit)


@router.get("/{note_id}", response_model=MedicalNoteResponse)
async def read_medical_note(note_id: int, db: AsyncSession = Depends(get_db)):
    db_note = await crud.get_medical_note(db, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Medical note not found")
    return db_note


@router.get("/by-appointment/{appointment_id}", response_model=MedicalNoteResponse)
async def read_medical_note_by_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    db_note = await crud.get_medical_note_by_appointment(db, appointment_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Medical note not found")
    return db_note


@router.post("/", response_model=MedicalNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_medical_note(note_in: MedicalNoteCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_medical_note(db, note_in)


@router.put("/{note_id}", response_model=MedicalNoteResponse)
async def update_medical_note(note_id: int, note_in: MedicalNoteUpdate, db: AsyncSession = Depends(get_db)):
    db_note = await crud.update_medical_note(db, note_id, note_in)
    if not db_note:
        raise HTTPException(status_code=404, detail="Medical note not found")
    return db_note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medical_note(note_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_medical_note(db, note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Medical note not found")
