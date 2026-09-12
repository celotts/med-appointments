from core import crud_doctor_schedule
from core.db import get_db
from fastapi import APIRouter, Depends, HTTPException
from schemas.doctor_schedule import (
    DoctorScheduleCreate,
    DoctorScheduleResponse,
    DoctorScheduleUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/doctor-schedules", tags=["Doctor Schedules"])


@router.get("/", response_model=list[DoctorScheduleResponse])
async def list_doctor_schedules(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await crud_doctor_schedule.get_doctor_schedules(db, skip, limit)


@router.get("/{schedule_id}", response_model=DoctorScheduleResponse)
async def get_doctor_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    schedule = await crud_doctor_schedule.get_doctor_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Doctor schedule not found")
    return schedule


@router.post("/", response_model=DoctorScheduleResponse, status_code=201)
async def create_doctor_schedule(
    schedule: DoctorScheduleCreate, db: AsyncSession = Depends(get_db)
):
    return await crud_doctor_schedule.create_doctor_schedule(db, schedule)


@router.put("/{schedule_id}", response_model=DoctorScheduleResponse)
async def update_doctor_schedule(
    schedule_id: str, schedule: DoctorScheduleUpdate, db: AsyncSession = Depends(get_db)
):
    db_schedule = await crud_doctor_schedule.get_doctor_schedule(db, schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Doctor schedule not found")
    return await crud_doctor_schedule.update_doctor_schedule(db, db_schedule, schedule)


@router.delete("/{schedule_id}", status_code=204)
async def delete_doctor_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    db_schedule = await crud_doctor_schedule.delete_doctor_schedule(db, schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Doctor schedule not found")
    return None
