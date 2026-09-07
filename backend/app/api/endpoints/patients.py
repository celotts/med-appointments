from typing import Any

from core import crud_patient
from dependencies import get_current_user, get_db
from dependencies_i18n import I18nResponse, get_language
from fastapi import APIRouter, Depends
from models.user import User as UserModel
from schemas.patient import Patient, PatientCreate, PatientUpdate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/",
    response_model=list[Patient],
    summary="Get a list of patients",
)
async def list_patients(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Gets a list of patients."""
    return await crud_patient.get_patients(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=Patient,
    status_code=201,
    summary="Create a new patient",
    responses={400: {"description": "Email is already registered."}},
)
async def create_patient(
    *,
    db: AsyncSession = Depends(get_db),
    patient_in: PatientCreate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Patient:
    """Creates a new patient."""
    i18n = I18nResponse(language)
    try:
        return await crud_patient.create_patient(db, patient=patient_in)
    except IntegrityError:
        raise i18n.error("patient_already_exists", status_code=400)


@router.get(
    "/{patient_id}",
    response_model=Patient,
    summary="Get a patient by ID",
    responses={404: {"description": "Patient not found."}},
)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Gets a patient by ID."""
    i18n = I18nResponse(language)
    patient = await crud_patient.get_patient(db, patient_id=patient_id)
    if not patient:
        raise i18n.error("patient_not_found", status_code=404)
    return patient


@router.put(
    "/{patient_id}",
    response_model=Patient,
    summary="Update an existing patient",
    responses={404: {"description": "Patient not found."}},
)
async def update_patient(
    *,
    db: AsyncSession = Depends(get_db),
    patient_id: int,
    patient_in: PatientUpdate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Updates an existing patient."""
    i18n = I18nResponse(language)
    db_patient = await crud_patient.get_patient(db, patient_id=patient_id)
    if not db_patient:
        raise i18n.error("patient_not_found", status_code=404)
    try:
        return await crud_patient.update_patient(
            db, db_patient=db_patient, patient=patient_in
        )
    except IntegrityError:
        raise i18n.error("patient_already_exists", status_code=400)


@router.delete(
    "/{patient_id}",
    response_model=Patient,
    summary="Delete a patient",
    responses={404: {"description": "Patient not found."}},
)
async def delete_patient(
    *,
    db: AsyncSession = Depends(get_db),
    patient_id: int,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Deletes a patient."""
    i18n = I18nResponse(language)
    patient = await crud_patient.delete_patient(db, patient_id=patient_id)
    if not patient:
        raise i18n.error("patient_not_found", status_code=404)
    return patient
