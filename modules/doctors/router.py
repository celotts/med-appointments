from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import DoctorCreate, DoctorUpdate, DoctorResponse
from . import crud

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("/", response_model=List[DoctorResponse])
async def read_doctors(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_doctors(db, skip=skip, limit=limit)


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def read_doctor(doctor_id: int, db: AsyncSession = Depends(get_db)):
    db_doctor = await crud.get_doctor(db, doctor_id)
    if not db_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_doctor


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(doctor_in: DoctorCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_doctor(db, doctor_in)


@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(doctor_id: int, doctor_in: DoctorUpdate, db: AsyncSession = Depends(get_db)):
    db_doctor = await crud.update_doctor(db, doctor_id, doctor_in)
    if not db_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_doctor


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(doctor_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_doctor(db, doctor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Doctor not found")
