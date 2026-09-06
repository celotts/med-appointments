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
    summary="Get a list of specialties",
)
async def read_specialties(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Gets a list of medical specialties."""
    return await crud_specialty.get_specialties(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=Specialty,
    status_code=201,
    summary="Create a new specialty",
    responses={
        400: {"description": "A specialty with that name already exists."},
    },
)
async def create_specialty(
    *,
    db: AsyncSession = Depends(get_db),
    specialty_in: SpecialtyCreate,
    current_user: UserModel = Depends(get_current_user),
) -> Specialty:
    """Creates a new medical specialty."""
    try:
        return await crud_specialty.create_specialty(db, specialty=specialty_in)
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="A specialty with that name already exists."
        )


@router.get(
    "/{specialty_id}",
    response_model=Specialty,
    summary="Get a specialty by ID",
    responses={
        404: {"description": "Specialty not found."},
    },
)
async def read_specialty_by_id(
    specialty_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Gets a specialty by ID."""
    specialty = await crud_specialty.get_specialty(db, specialty_id=specialty_id)
    if not specialty:
        raise HTTPException(status_code=404, detail="Specialty not found.")
    return specialty


@router.put(
    "/{specialty_id}",
    response_model=Specialty,
    summary="Update an existing specialty",
    responses={
        404: {"description": "Specialty not found."},
    },
)
async def update_specialty(
    *,
    db: AsyncSession = Depends(get_db),
    specialty_id: int,
    specialty_in: SpecialtyUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Updates an existing specialty."""
    db_specialty = await crud_specialty.get_specialty(db, specialty_id=specialty_id)
    if not db_specialty:
        raise HTTPException(status_code=404, detail="Specialty not found.")
    try:
        return await crud_specialty.update_specialty(
            db, db_specialty=db_specialty, specialty=specialty_in
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="A specialty with that name already exists."
        )


@router.delete(
    "/{specialty_id}",
    response_model=Specialty,
    summary="Delete a specialty",
    responses={
        404: {"description": "Specialty not found."},
    },
)
async def delete_specialty(
    *,
    db: AsyncSession = Depends(get_db),
    specialty_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Deletes a specialty."""
    specialty = await crud_specialty.delete_specialty(db, specialty_id=specialty_id)
    if not specialty:
        raise HTTPException(status_code=404, detail="Specialty not found.")
    return specialty
