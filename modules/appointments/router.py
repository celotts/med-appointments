from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from . import crud

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/", response_model=List[AppointmentResponse])
async def read_appointments(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_appointments(db, skip=skip, limit=limit)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def read_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    db_appointment = await crud.get_appointment(db, appointment_id)
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return db_appointment


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(appointment_in: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_appointment(db, appointment_in)


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(appointment_id: int, appointment_in: AppointmentUpdate, db: AsyncSession = Depends(get_db)):
    db_appointment = await crud.update_appointment(db, appointment_id, appointment_in)
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return db_appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_appointment(db, appointment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Appointment not found")
