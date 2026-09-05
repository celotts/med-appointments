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
        raise HTTPException(status_code=404, detail="Especialidad no encontrada.")


@router.get(
    "/",
    response_model=list[Medico],
    summary="Obtener una lista de médicos",
)
async def read_medicos(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    especialidad_id: int | None = None,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Obtiene una lista de médicos, opcionalmente filtrada por especialidad."""
    if especialidad_id is not None:
        return await crud_medico.get_medicos_by_especialidad(
            db, especialidad_id=especialidad_id, skip=skip, limit=limit
        )
    return await crud_medico.get_medicos(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=Medico,
    status_code=201,
    summary="Crear un nuevo médico",
    responses={
        400: {"description": "Email o cédula profesional ya registrados."},
        404: {"description": "Especialidad no encontrada."},
    },
)
async def create_medico(
    *,
    db: AsyncSession = Depends(get_db),
    medico_in: MedicoCreate,
    current_user: UserModel = Depends(get_current_user),
) -> Medico:
    """Crea un nuevo médico."""
    await _ensure_especialidad(db, medico_in.especialidad_id)
    try:
        return await crud_medico.create_medico(db, medico=medico_in)
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Email o cédula profesional ya registrados."
        )


@router.get(
    "/{medico_id}",
    response_model=Medico,
    summary="Obtener un médico por su ID",
    responses={404: {"description": "El médico no fue encontrado."}},
)
async def read_medico_by_id(
    medico_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Obtiene un médico por su ID."""
    medico = await crud_medico.get_medico(db, medico_id=medico_id)
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado.")
    return medico


@router.put(
    "/{medico_id}",
    response_model=Medico,
    summary="Actualizar un médico existente",
    responses={404: {"description": "El médico no fue encontrado."}},
)
async def update_medico(
    *,
    db: AsyncSession = Depends(get_db),
    medico_id: int,
    medico_in: MedicoUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Actualiza un médico existente."""
    db_medico = await crud_medico.get_medico(db, medico_id=medico_id)
    if not db_medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado.")
    if medico_in.especialidad_id is not None:
        await _ensure_especialidad(db, medico_in.especialidad_id)
    try:
        return await crud_medico.update_medico(
            db, db_medico=db_medico, medico=medico_in
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Email o cédula profesional ya registrados."
        )


@router.delete(
    "/{medico_id}",
    response_model=Medico,
    summary="Eliminar un médico",
    responses={404: {"description": "El médico no fue encontrado."}},
)
async def delete_medico(
    *,
    db: AsyncSession = Depends(get_db),
    medico_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Elimina un médico."""
    medico = await crud_medico.delete_medico(db, medico_id=medico_id)
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado.")
    return medico
