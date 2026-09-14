from core import crud_doctor_schedule
from core.db import get_db
from dependencies import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from models.user import User
from schemas.doctor_schedule import (
    DoctorScheduleCreate,
    DoctorScheduleResponse,
    DoctorScheduleUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/doctor-schedules", tags=["Doctor Schedules"])


@router.get("/", response_model=list[DoctorScheduleResponse])
async def list_doctor_schedules(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud_doctor_schedule.get_doctor_schedules(
        db, skip, limit, user_id=current_user.id
    )


@router.get("/{schedule_id}", response_model=DoctorScheduleResponse)
async def get_doctor_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = await crud_doctor_schedule.get_doctor_schedule(
        db, schedule_id, user_id=current_user.id
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Doctor schedule not found")
    return schedule


@router.post("/", response_model=DoctorScheduleResponse, status_code=201)
async def create_doctor_schedule(
    schedule: DoctorScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud_doctor_schedule.create_doctor_schedule(
        db, schedule, user_id=current_user.id
    )


@router.put("/{schedule_id}", response_model=DoctorScheduleResponse)
async def update_doctor_schedule(
    schedule_id: str,
    schedule: DoctorScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_schedule = await crud_doctor_schedule.get_doctor_schedule(
        db, schedule_id, user_id=current_user.id
    )
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Doctor schedule not found")
    return await crud_doctor_schedule.update_doctor_schedule(db, db_schedule, schedule)


@router.delete("/{schedule_id}", status_code=204)
async def delete_doctor_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_schedule = await crud_doctor_schedule.delete_doctor_schedule(
        db, schedule_id, user_id=current_user.id
    )
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Doctor schedule not found")
    return None
