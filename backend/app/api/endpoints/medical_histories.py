from core import crud_medical_history
from core.db import get_db
from fastapi import APIRouter, Depends, HTTPException
from schemas.medical_history import (
    MedicalHistoryCreate,
    MedicalHistoryResponse,
    MedicalHistoryUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/medical-histories", tags=["Medical Histories"])


@router.get("/", response_model=list[MedicalHistoryResponse])
async def list_medical_histories(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await crud_medical_history.get_medical_histories(db, skip, limit)


@router.get("/{history_id}", response_model=MedicalHistoryResponse)
async def get_medical_history(history_id: str, db: AsyncSession = Depends(get_db)):
    history = await crud_medical_history.get_medical_history(db, history_id)
    if not history:
        raise HTTPException(status_code=404, detail="Medical history not found")
    return history


@router.post("/", response_model=MedicalHistoryResponse, status_code=201)
async def create_medical_history(
    history: MedicalHistoryCreate, db: AsyncSession = Depends(get_db)
):
    return await crud_medical_history.create_medical_history(db, history)


@router.put("/{history_id}", response_model=MedicalHistoryResponse)
async def update_medical_history(
    history_id: str, history: MedicalHistoryUpdate, db: AsyncSession = Depends(get_db)
):
    db_history = await crud_medical_history.get_medical_history(db, history_id)
    if not db_history:
        raise HTTPException(status_code=404, detail="Medical history not found")
    return await crud_medical_history.update_medical_history(db, db_history, history)


@router.delete("/{history_id}", status_code=204)
async def delete_medical_history(history_id: str, db: AsyncSession = Depends(get_db)):
    db_history = await crud_medical_history.delete_medical_history(db, history_id)
    if not db_history:
        raise HTTPException(status_code=404, detail="Medical history not found")
    return None
