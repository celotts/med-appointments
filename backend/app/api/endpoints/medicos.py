from typing import Any

from core import crud_medico, crud_specialty
from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException
from models.user import User as UserModel
from schemas.medico import Medico, MedicoCreate, MedicoUpdate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


async def _ensure_especialidad(db: AsyncSession, especialidad_id: int) -> None:
    if not await crud_specialty.get_specialty(db, especialidad_id):
        raise HTTPException(status_code=404, detail="Specialty not found.")


@router.get(
    "/",
    response_model=list[Medico],
    summary="Get a list of doctors",
)
async def read_medicos(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    especialidad_id: int | None = None,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Gets a list of doctors, optionally filtered by specialty."""
    if especialidad_id is not None:
        return await crud_medico.get_medicos_by_especialidad(
            db, especialidad_id=especialidad_id, skip=skip, limit=limit
        )
    return await crud_medico.get_medicos(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=Medico,
    status_code=201,
    summary="Create a new doctor",
    responses={
        400: {"description": "Email or professional license already registered."},
        404: {"description": "Specialty not found."},
    },
)
async def create_medico(
    *,
    db: AsyncSession = Depends(get_db),
    medico_in: MedicoCreate,
    current_user: UserModel = Depends(get_current_user),
) -> Medico:
    """Creates a new doctor."""
    await _ensure_especialidad(db, medico_in.especialidad_id)
    try:
        return await crud_medico.create_medico(db, medico=medico_in)
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Email or professional license already registered."
        )


@router.get(
    "/{medico_id}",
    response_model=Medico,
    summary="Get a doctor by ID",
    responses={404: {"description": "Doctor not found."}},
)
async def read_medico_by_id(
    medico_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Gets a doctor by ID."""
    medico = await crud_medico.get_medico(db, medico_id=medico_id)
    if not medico:
        raise HTTPException(status_code=404, detail="Doctor not found.")
    return medico


@router.put(
    "/{medico_id}",
    response_model=Medico,
    summary="Update an existing doctor",
    responses={404: {"description": "Doctor not found."}},
)
async def update_medico(
    *,
    db: AsyncSession = Depends(get_db),
    medico_id: int,
    medico_in: MedicoUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Updates an existing doctor."""
    db_medico = await crud_medico.get_medico(db, medico_id=medico_id)
    if not db_medico:
        raise HTTPException(status_code=404, detail="Doctor not found.")
    if medico_in.especialidad_id is not None:
        await _ensure_especialidad(db, medico_in.especialidad_id)
    try:
        return await crud_medico.update_medico(
            db, db_medico=db_medico, medico=medico_in
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Email or professional license already registered."
        )


@router.delete(
    "/{medico_id}",
    response_model=Medico,
    summary="Delete a doctor",
    responses={404: {"description": "Doctor not found."}},
)
async def delete_medico(
    *,
    db: AsyncSession = Depends(get_db),
    medico_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Deletes a doctor."""
    medico = await crud_medico.delete_medico(db, medico_id=medico_id)
    if not medico:
        raise HTTPException(status_code=404, detail="Doctor not found.")
    return medico
