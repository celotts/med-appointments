from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import PatientCreate, PatientUpdate, PatientResponse
from . import crud

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("/", response_model=List[PatientResponse])
async def read_patients(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_patients(db, skip=skip, limit=limit)


@router.get("/{patient_id}", response_model=PatientResponse)
async def read_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    db_patient = await crud.get_patient(db, patient_id)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(patient_in: PatientCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_patient(db, patient_in)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: int, patient_in: PatientUpdate, db: AsyncSession = Depends(get_db)):
    db_patient = await crud.update_patient(db, patient_id, patient_in)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_patient(db, patient_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found")
