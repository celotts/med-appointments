from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import SpecialtyCreate, SpecialtyUpdate, SpecialtyResponse
from . import crud

router = APIRouter(prefix="/specialties", tags=["Specialties"])


@router.get("/", response_model=List[SpecialtyResponse])
async def read_specialties(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_specialties(db, skip=skip, limit=limit)


@router.get("/{specialty_id}", response_model=SpecialtyResponse)
async def read_specialty(specialty_id: int, db: AsyncSession = Depends(get_db)):
    db_specialty = await crud.get_specialty(db, specialty_id)
    if not db_specialty:
        raise HTTPException(status_code=404, detail="Specialty not found")
    return db_specialty


@router.post("/", response_model=SpecialtyResponse, status_code=status.HTTP_201_CREATED)
async def create_specialty(specialty_in: SpecialtyCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_specialty(db, specialty_in)


@router.put("/{specialty_id}", response_model=SpecialtyResponse)
async def update_specialty(specialty_id: int, specialty_in: SpecialtyUpdate, db: AsyncSession = Depends(get_db)):
    db_specialty = await crud.update_specialty(db, specialty_id, specialty_in)
    if not db_specialty:
        raise HTTPException(status_code=404, detail="Specialty not found")
    return db_specialty


@router.delete("/{specialty_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_specialty(specialty_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_specialty(db, specialty_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Specialty not found")
