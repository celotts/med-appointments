from __future__ import annotations

from core.db import get_db
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .schemas import DoctorCreate, DoctorResponse

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("/", response_model=list[DoctorResponse])
async def read_doctors(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all doctors.
    """
    return await crud.get_doctors(db, skip=skip, limit=limit)


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(doctor_in: DoctorCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new doctor.
    """
    return await crud.create_doctor(db, doctor_in)
