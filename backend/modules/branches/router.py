from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import BranchCreate, BranchUpdate, BranchResponse
from . import crud

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("/", response_model=List[BranchResponse])
async def read_branches(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_branches(db, skip=skip, limit=limit)


@router.get("/{branch_id}", response_model=BranchResponse)
async def read_branch(branch_id: int, db: AsyncSession = Depends(get_db)):
    db_branch = await crud.get_branch(db, branch_id)
    if not db_branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return db_branch


@router.post("/", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(branch_in: BranchCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_branch(db, branch_in)


@router.put("/{branch_id}", response_model=BranchResponse)
async def update_branch(branch_id: int, branch_in: BranchUpdate, db: AsyncSession = Depends(get_db)):
    db_branch = await crud.update_branch(db, branch_id, branch_in)
    if not db_branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return db_branch


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(branch_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_branch(db, branch_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Branch not found")
