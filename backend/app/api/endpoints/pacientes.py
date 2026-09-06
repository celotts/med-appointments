from typing import Any

from core import crud_paciente
from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException
from models.user import User as UserModel
from schemas.paciente import Paciente, PacienteCreate, PacienteUpdate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/",
    response_model=list[Paciente],
    summary="Get a list of patients",
)
async def read_pacientes(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Gets a list of patients."""
    return await crud_paciente.get_pacientes(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=Paciente,
    status_code=201,
    summary="Create a new patient",
    responses={400: {"description": "Email is already registered."}},
)
async def create_paciente(
    *,
    db: AsyncSession = Depends(get_db),
    paciente_in: PacienteCreate,
    current_user: UserModel = Depends(get_current_user),
) -> Paciente:
    """Creates a new patient."""
    try:
        return await crud_paciente.create_paciente(db, paciente=paciente_in)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Email is already registered.")


@router.get(
    "/{paciente_id}",
    response_model=Paciente,
    summary="Get a patient by ID",
    responses={404: {"description": "Patient not found."}},
)
async def read_paciente_by_id(
    paciente_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Gets a patient by ID."""
    paciente = await crud_paciente.get_paciente(db, paciente_id=paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return paciente


@router.put(
    "/{paciente_id}",
    response_model=Paciente,
    summary="Update an existing patient",
    responses={404: {"description": "Patient not found."}},
)
async def update_paciente(
    *,
    db: AsyncSession = Depends(get_db),
    paciente_id: int,
    paciente_in: PacienteUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Updates an existing patient."""
    db_paciente = await crud_paciente.get_paciente(db, paciente_id=paciente_id)
    if not db_paciente:
        raise HTTPException(status_code=404, detail="Patient not found.")
    try:
        return await crud_paciente.update_paciente(
            db, db_paciente=db_paciente, paciente=paciente_in
        )
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Email is already registered.")


@router.delete(
    "/{paciente_id}",
    response_model=Paciente,
    summary="Delete a patient",
    responses={404: {"description": "Patient not found."}},
)
async def delete_paciente(
    *,
    db: AsyncSession = Depends(get_db),
    paciente_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Deletes a patient."""
    paciente = await crud_paciente.delete_paciente(db, paciente_id=paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return paciente
