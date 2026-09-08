from __future__ import annotations

from core.db import get_db
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .schemas import SpecialtyCreate, SpecialtyResponse

router = APIRouter(prefix="/specialties", tags=["Specialties"])


@router.get("/", response_model=list[SpecialtyResponse])
async def read_specialties(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all specialties.
    """
    return await crud.get_specialties(db, skip=skip, limit=limit)


@router.post("/", response_model=SpecialtyResponse, status_code=status.HTTP_201_CREATED)
async def create_specialty(
    specialty_in: SpecialtyCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create a new medical specialty.
    """
    return await crud.create_specialty(db, specialty_in)
