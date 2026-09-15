from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import AppointmentStatusCreate, AppointmentStatusUpdate, AppointmentStatusResponse
from . import crud

router = APIRouter(prefix="/appointment-statuses", tags=["Appointment Statuses"])


@router.get("/", response_model=List[AppointmentStatusResponse])
async def read_appointment_statuses(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_appointment_statuses(db, skip=skip, limit=limit)


@router.get("/{status_id}", response_model=AppointmentStatusResponse)
async def read_appointment_status(status_id: int, db: AsyncSession = Depends(get_db)):
    db_status = await crud.get_appointment_status(db, status_id)
    if not db_status:
        raise HTTPException(status_code=404, detail="Appointment status not found")
    return db_status


@router.post("/", response_model=AppointmentStatusResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment_status(status_in: AppointmentStatusCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_appointment_status(db, status_in)


@router.put("/{status_id}", response_model=AppointmentStatusResponse)
async def update_appointment_status(status_id: int, status_in: AppointmentStatusUpdate, db: AsyncSession = Depends(get_db)):
    db_status = await crud.update_appointment_status(db, status_id, status_in)
    if not db_status:
        raise HTTPException(status_code=404, detail="Appointment status not found")
    return db_status


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment_status(status_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_appointment_status(db, status_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Appointment status not found")
