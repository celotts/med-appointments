from typing import Any

from core import crud_doctor, crud_specialty
from dependencies import get_current_user, get_db
from dependencies_i18n import get_language, I18nResponse
from fastapi import APIRouter, Depends, HTTPException
from models.user import User as UserModel
from schemas.doctor import Doctor, DoctorCreate, DoctorUpdate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


async def _ensure_specialty(db: AsyncSession, specialty_id: int, i18n: I18nResponse) -> None:
    if not await crud_specialty.get_specialty(db, specialty_id):
        raise i18n.error("specialty_not_found", status_code=404)


@router.get(
    "/",
    response_model=list[Doctor],
    summary="Get a list of doctors",
)
async def list_doctors(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    specialty_id: int | None = None,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Gets a list of doctors, optionally filtered by specialty."""
    if specialty_id is not None:
        return await crud_doctor.get_doctors_by_specialty(
            db, specialty_id=specialty_id, skip=skip, limit=limit
        )
    return await crud_doctor.get_doctors(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=Doctor,
    status_code=201,
    summary="Create a new doctor",
    responses={
        400: {"description": "Email or professional license already registered."},
        404: {"description": "Specialty not found."},
    },
)
async def create_doctor(
    *,
    db: AsyncSession = Depends(get_db),
    doctor_in: DoctorCreate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Doctor:
    """Creates a new doctor."""
    i18n = I18nResponse(language)
    await _ensure_specialty(db, doctor_in.specialty_id, i18n)
    try:
        return await crud_doctor.create_doctor(db, doctor=doctor_in)
    except IntegrityError:
        raise i18n.error("doctor_already_exists", status_code=400)


@router.get(
    "/{doctor_id}",
    response_model=Doctor,
    summary="Get a doctor by ID",
    responses={404: {"description": "Doctor not found."}},
)
async def get_doctor(
    doctor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Gets a doctor by ID."""
    i18n = I18nResponse(language)
    doctor = await crud_doctor.get_doctor(db, doctor_id=doctor_id)
    if not doctor:
        raise i18n.error("doctor_not_found", status_code=404)
    return doctor


@router.put(
    "/{doctor_id}",
    response_model=Doctor,
    summary="Update an existing doctor",
    responses={404: {"description": "Doctor not found."}},
)
async def update_doctor(
    *,
    db: AsyncSession = Depends(get_db),
    doctor_id: int,
    doctor_in: DoctorUpdate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Updates an existing doctor."""
    i18n = I18nResponse(language)
    db_doctor = await crud_doctor.get_doctor(db, doctor_id=doctor_id)
    if not db_doctor:
        raise i18n.error("doctor_not_found", status_code=404)
    if doctor_in.specialty_id is not None:
        await _ensure_specialty(db, doctor_in.specialty_id, i18n)
    try:
        return await crud_doctor.update_doctor(
            db, db_doctor=db_doctor, doctor=doctor_in
        )
    except IntegrityError:
        raise i18n.error("doctor_already_exists", status_code=400)


@router.delete(
    "/{doctor_id}",
    response_model=Doctor,
    summary="Delete a doctor",
    responses={404: {"description": "Doctor not found."}},
)
async def delete_doctor(
    *,
    db: AsyncSession = Depends(get_db),
    doctor_id: int,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Deletes a doctor."""
    i18n = I18nResponse(language)
    doctor = await crud_doctor.delete_doctor(db, doctor_id=doctor_id)
    if not doctor:
        raise i18n.error("doctor_not_found", status_code=404)
    return doctor
