from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import WaitlistCreate, WaitlistUpdate, WaitlistResponse
from . import crud

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.get("/", response_model=List[WaitlistResponse])
async def read_waitlist_entries(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_waitlist_entries(db, skip=skip, limit=limit)


@router.get("/{entry_id}", response_model=WaitlistResponse)
async def read_waitlist_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    db_entry = await crud.get_waitlist_entry(db, entry_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return db_entry


@router.post("/", response_model=WaitlistResponse, status_code=status.HTTP_201_CREATED)
async def create_waitlist_entry(entry_in: WaitlistCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_waitlist_entry(db, entry_in)


@router.put("/{entry_id}", response_model=WaitlistResponse)
async def update_waitlist_entry(entry_id: int, entry_in: WaitlistUpdate, db: AsyncSession = Depends(get_db)):
    db_entry = await crud.update_waitlist_entry(db, entry_id, entry_in)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return db_entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_waitlist_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_waitlist_entry(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
