from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db, get_current_user
from core import crud_cita, crud_medico, crud_nota_medica, crud_paciente
from models.user import User as UserModel
from schemas.cita import (
    CitaCreate,
    CitaEstadoUpdate,
    CitaOut,
    CitaUpdate,
    NotaMedicaCreate,
    NotaMedicaOut,
    NotaMedicaUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["Citas"])


def _busy_error(exc: ValueError) -> HTTPException:
    if "cita en ese horario" in str(exc):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/citas/",
    response_model=list[CitaOut],
    summary="Obtener una lista de citas",
)
async def read_citas(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    paciente_id: int | None = None,
    medico_id: int | None = None,
    estado: str | None = None,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Lista de citas con filtros opcionales por paciente, médico y estado."""
    return await crud_cita.get_citas(
        db,
        skip=skip,
        limit=limit,
        paciente_id=paciente_id,
        medico_id=medico_id,
        estado=estado,
    )


@router.post(
    "/citas/",
    response_model=CitaOut,
    status_code=201,
    summary="Agendar una nueva cita",
    responses={
        400: {"description": "Datos inválidos."},
        404: {"description": "Paciente o médico no encontrado."},
        409: {"description": "El médico ya tiene una cita en ese horario."},
    },
)
async def create_cita(
    *,
    db: AsyncSession = Depends(get_db),
    cita_in: CitaCreate,
    current_user: UserModel = Depends(get_current_user),
) -> CitaOut:
    """Agenda una nueva cita en estado PENDIENTE."""
    if not await crud_paciente.get_paciente(db, cita_in.paciente_id):
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    if not await crud_medico.get_medico(db, cita_in.medico_id):
        raise HTTPException(status_code=404, detail="Médico no encontrado.")
    try:
        return await crud_cita.create_cita(db, cita=cita_in)
    except ValueError as exc:
        raise _busy_error(exc)


@router.get(
    "/citas/{cita_id}",
    response_model=CitaOut,
    summary="Obtener una cita por su ID",
    responses={404: {"description": "La cita no fue encontrada."}},
)
async def read_cita_by_id(
    cita_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Obtiene una cita por su ID."""
    cita = await crud_cita.get_cita(db, cita_id)
    if not cita:
        raise HTTPException(status_code=404, detail="CitaOut no encontrada.")
    return cita


@router.put(
    "/citas/{cita_id}",
    response_model=CitaOut,
    summary="Reagendar una cita",
    responses={
        400: {"description": "No se puede reagendar o datos inválidos."},
        404: {"description": "La cita no fue encontrada."},
        409: {"description": "El médico ya tiene una cita en ese horario."},
    },
)
async def reagendar_cita(
    *,
    db: AsyncSession = Depends(get_db),
    cita_id: int,
    cita_in: CitaUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Reagenda una cita y la transiciona a estado REAGENDADA."""
    db_cita = await crud_cita.get_cita(db, cita_id)
    if not db_cita:
        raise HTTPException(status_code=404, detail="CitaOut no encontrada.")
    try:
        return await crud_cita.reagendar_cita(db, db_cita, cita_in)
    except ValueError as exc:
        raise _busy_error(exc)


@router.patch(
    "/citas/{cita_id}/estado",
    response_model=CitaOut,
    summary="Cambiar el estado de una cita",
    responses={
        400: {"description": "Transición de estado inválida."},
        404: {"description": "La cita no fue encontrada."},
    },
)
async def change_cita_estado(
    *,
    db: AsyncSession = Depends(get_db),
    cita_id: int,
    cambio: CitaEstadoUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Cambia el estado de una cita siguiendo las transiciones válidas."""
    db_cita = await crud_cita.get_cita(db, cita_id)
    if not db_cita:
        raise HTTPException(status_code=404, detail="CitaOut no encontrada.")
    try:
        return await crud_cita.change_estado(db, db_cita, cambio)
    except ValueError as exc:
        raise _busy_error(exc)


@router.delete(
    "/citas/{cita_id}",
    summary="Eliminar una cita",
    responses={404: {"description": "La cita no fue encontrada."}},
)
async def delete_cita(
    *,
    db: AsyncSession = Depends(get_db),
    cita_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, str]:
    """Elimina una cita."""
    db_cita = await crud_cita.get_cita(db, cita_id)
    if not db_cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada.")
    await crud_cita.delete_cita(db, db_cita)
    return {"detail": "Cita eliminada."}


# ---------- Notas médicas ----------
@router.get(
    "/notas/",
    response_model=list[NotaMedicaOut],
    summary="Obtener notas médicas",
)
async def read_notas(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    cita_id: int | None = None,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Lista de notas médicas, opcionalmente filtradas por cita."""
    return await crud_nota_medica.get_notas(
        db, skip=skip, limit=limit, cita_id=cita_id
    )


@router.post(
    "/notas/",
    response_model=NotaMedicaOut,
    status_code=201,
    summary="Crear una nota médica",
    responses={
        400: {"description": "La cita ya tiene una nota médica."},
        404: {"description": "La cita no fue encontrada."},
    },
)
async def create_nota(
    *,
    db: AsyncSession = Depends(get_db),
    nota_in: NotaMedicaCreate,
    current_user: UserModel = Depends(get_current_user),
) -> NotaMedicaOut:
    """Crea una nota médica para una cita (una por cita)."""
    cita = await crud_cita.get_cita(db, nota_in.cita_id)
    if not cita:
        raise HTTPException(status_code=404, detail="CitaOut no encontrada.")
    if await crud_nota_medica.get_nota_by_cita(db, nota_in.cita_id):
        raise HTTPException(
            status_code=400, detail="La cita ya tiene una nota médica."
        )
    try:
        return await crud_nota_medica.create_nota(db, nota=nota_in)
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="La cita ya tiene una nota médica."
        )


@router.get(
    "/notas/{nota_id}",
    response_model=NotaMedicaOut,
    summary="Obtener una nota médica por su ID",
    responses={404: {"description": "La nota no fue encontrada."}},
)
async def read_nota_by_id(
    nota_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Obtiene una nota médica por su ID."""
    nota = await crud_nota_medica.get_nota(db, nota_id)
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    return nota


@router.put(
    "/notas/{nota_id}",
    response_model=NotaMedicaOut,
    summary="Actualizar una nota médica",
    responses={404: {"description": "La nota no fue encontrada."}},
)
async def update_nota(
    *,
    db: AsyncSession = Depends(get_db),
    nota_id: int,
    nota_in: NotaMedicaUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Actualiza una nota médica existente."""
    db_nota = await crud_nota_medica.get_nota(db, nota_id)
    if not db_nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    return await crud_nota_medica.update_nota(db, db_nota, nota_in)


@router.delete(
    "/notas/{nota_id}",
    response_model=NotaMedicaOut,
    summary="Eliminar una nota médica",
    responses={404: {"description": "La nota no fue encontrada."}},
)
async def delete_nota(
    *,
    db: AsyncSession = Depends(get_db),
    nota_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Elimina una nota médica."""
    nota = await crud_nota_medica.delete_nota(db, nota_id)
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    return nota
