from __future__ import annotations

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from .schemas import RoleCreate, RoleUpdate, RoleResponse
from . import crud

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=List[RoleResponse])
async def read_roles(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_roles(db, skip=skip, limit=limit)


@router.get("/{role_id}", response_model=RoleResponse)
async def read_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    db_role = await crud.get_role(db, role_id)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(role_in: RoleCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_role(db, role_in)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(role_id: uuid.UUID, role_in: RoleUpdate, db: AsyncSession = Depends(get_db)):
    db_role = await crud.update_role(db, role_id, role_in)
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_role(db, role_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Role not found")
