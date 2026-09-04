from typing import Any

from core import crud_specialty
from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException
from models.user import User as UserModel
from schemas.specialty import Specialty, SpecialtyCreate, SpecialtyUpdate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/",
    response_model=list[Specialty],
    summary="Obtener una lista de especialidades",
)
async def read_specialties(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Obtiene una lista de especialidades médicas."""
    return await crud_specialty.get_specialties(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=Specialty,
    status_code=201,
    summary="Crear una nueva especialidad",
    responses={
        400: {"description": "Ya existe una especialidad con ese nombre."},
    },
)
async def create_specialty(
    *,
    db: AsyncSession = Depends(get_db),
    specialty_in: SpecialtyCreate,
    current_user: UserModel = Depends(get_current_user),
) -> Specialty:
    """Crea una nueva especialidad médica."""
    try:
        return await crud_specialty.create_specialty(db, specialty=specialty_in)
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Ya existe una especialidad con ese nombre."
        )


@router.get(
    "/{specialty_id}",
    response_model=Specialty,
    summary="Obtener una especialidad por su ID",
    responses={
        404: {"description": "La especialidad no fue encontrada."},
    },
)
async def read_specialty_by_id(
    specialty_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Obtiene una especialidad por su ID."""
    specialty = await crud_specialty.get_specialty(db, specialty_id=specialty_id)
    if not specialty:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada.")
    return specialty


@router.put(
    "/{specialty_id}",
    response_model=Specialty,
    summary="Actualizar una especialidad existente",
    responses={
        404: {"description": "La especialidad no fue encontrada."},
    },
)
async def update_specialty(
    *,
    db: AsyncSession = Depends(get_db),
    specialty_id: int,
    specialty_in: SpecialtyUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Actualiza una especialidad existente."""
    db_specialty = await crud_specialty.get_specialty(db, specialty_id=specialty_id)
    if not db_specialty:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada.")
    try:
        return await crud_specialty.update_specialty(
            db, db_specialty=db_specialty, specialty=specialty_in
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Ya existe una especialidad con ese nombre."
        )


@router.delete(
    "/{specialty_id}",
    response_model=Specialty,
    summary="Eliminar una especialidad",
    responses={
        404: {"description": "La especialidad no fue encontrada."},
    },
)
async def delete_specialty(
    *,
    db: AsyncSession = Depends(get_db),
    specialty_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Elimina una especialidad."""
    specialty = await crud_specialty.delete_specialty(db, specialty_id=specialty_id)
    if not specialty:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada.")
    return specialty
