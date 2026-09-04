from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db, get_current_user
from core import crud_paciente
from models.user import User as UserModel
from schemas.paciente import Paciente, PacienteCreate, PacienteUpdate

router = APIRouter()


@router.get(
    "/",
    response_model=list[Paciente],
    summary="Obtener una lista de pacientes",
)
async def read_pacientes(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Obtiene una lista de pacientes."""
    return await crud_paciente.get_pacientes(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=Paciente,
    status_code=201,
    summary="Crear un nuevo paciente",
    responses={400: {"description": "El email ya está registrado."}},
)
async def create_paciente(
    *,
    db: AsyncSession = Depends(get_db),
    paciente_in: PacienteCreate,
    current_user: UserModel = Depends(get_current_user),
) -> Paciente:
    """Crea un nuevo paciente."""
    try:
        return await crud_paciente.create_paciente(db, paciente=paciente_in)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="El email ya está registrado.")


@router.get(
    "/{paciente_id}",
    response_model=Paciente,
    summary="Obtener un paciente por su ID",
    responses={404: {"description": "El paciente no fue encontrado."}},
)
async def read_paciente_by_id(
    paciente_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Obtiene un paciente por su ID."""
    paciente = await crud_paciente.get_paciente(db, paciente_id=paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    return paciente


@router.put(
    "/{paciente_id}",
    response_model=Paciente,
    summary="Actualizar un paciente existente",
    responses={404: {"description": "El paciente no fue encontrado."}},
)
async def update_paciente(
    *,
    db: AsyncSession = Depends(get_db),
    paciente_id: int,
    paciente_in: PacienteUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Actualiza un paciente existente."""
    db_paciente = await crud_paciente.get_paciente(db, paciente_id=paciente_id)
    if not db_paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    try:
        return await crud_paciente.update_paciente(
            db, db_paciente=db_paciente, paciente=paciente_in
        )
    except IntegrityError:
        raise HTTPException(status_code=400, detail="El email ya está registrado.")


@router.delete(
    "/{paciente_id}",
    response_model=Paciente,
    summary="Eliminar un paciente",
    responses={404: {"description": "El paciente no fue encontrado."}},
)
async def delete_paciente(
    *,
    db: AsyncSession = Depends(get_db),
    paciente_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Elimina un paciente."""
    paciente = await crud_paciente.delete_paciente(db, paciente_id=paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    return paciente
