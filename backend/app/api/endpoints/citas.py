from core import crud_cita, crud_medico, crud_nota_medica, crud_paciente
from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["Appointments"])


@router.get(
    "/citas/",
    response_model=list[CitaOut],
    summary="Get a list of appointments",
)
async def read_citas(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    paciente_id: int | None = None,
    medico_id: int | None = None,
    estado: str | None = None,
    current_user: UserModel = Depends(get_current_user),
) -> list[CitaOut]:
    """List of appointments with optional filters by patient, doctor, and status."""
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
    summary="Schedule a new appointment",
    responses={
        400: {"description": "Invalid data."},
        404: {"description": "Patient or doctor not found."},
        409: {"description": "The doctor already has an appointment at that time."},
    },
)
async def create_cita(
    *,
    db: AsyncSession = Depends(get_db),
    cita_in: CitaCreate,
    current_user: UserModel = Depends(get_current_user),
) -> CitaOut:
    """Schedules a new appointment in PENDING status."""
    if not await crud_paciente.get_paciente(db, cita_in.paciente_id):
        raise HTTPException(status_code=404, detail="Patient not found.")
    if not await crud_medico.get_medico(db, cita_in.medico_id):
        raise HTTPException(status_code=404, detail="Doctor not found.")
    try:
        return await crud_cita.create_cita(db, cita=cita_in)
    except ValueError as exc:
        if "cita en ese horario" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/citas/{cita_id}",
    response_model=CitaOut,
    summary="Get an appointment by ID",
    responses={404: {"description": "Appointment not found."}},
)
async def read_cita_by_id(
    cita_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> CitaOut:
    """Gets an appointment by ID."""
    cita = await crud_cita.get_cita(db, cita_id)
    if not cita:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    return cita


@router.put(
    "/citas/{cita_id}",
    response_model=CitaOut,
    summary="Reschedule an appointment",
    responses={
        400: {"description": "Cannot reschedule or invalid data."},
        404: {"description": "Appointment not found."},
        409: {"description": "The doctor already has an appointment at that time."},
    },
)
async def reagendar_cita(
    *,
    db: AsyncSession = Depends(get_db),
    cita_id: int,
    cita_in: CitaUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> CitaOut:
    """Reschedules an appointment and transitions it to RESCHEDULED status."""
    db_cita = await crud_cita.get_cita(db, cita_id)
    if not db_cita:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    try:
        return await crud_cita.reagendar_cita(db, db_cita, cita_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/citas/{cita_id}/estado",
    response_model=CitaOut,
    summary="Change appointment status",
    responses={
        400: {"description": "Invalid status transition."},
        404: {"description": "Appointment not found."},
    },
)
async def change_cita_estado(
    *,
    db: AsyncSession = Depends(get_db),
    cita_id: int,
    cambio: CitaEstadoUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> CitaOut:
    """Changes appointment status following valid transitions."""
    db_cita = await crud_cita.get_cita(db, cita_id)
    if not db_cita:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    try:
        return await crud_cita.change_estado(db, db_cita, cambio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/citas/{cita_id}",
    summary="Delete an appointment",
    responses={404: {"description": "Appointment not found."}},
)
async def delete_cita(
    *,
    db: AsyncSession = Depends(get_db),
    cita_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, str]:
    """Deletes an appointment."""
    db_cita = await crud_cita.get_cita(db, cita_id)
    if not db_cita:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    await crud_cita.delete_cita(db, db_cita)
    return {"detail": "Appointment deleted."}


# ---------- Medical notes ----------
@router.get(
    "/notas/",
    response_model=list[NotaMedicaOut],
    summary="Get medical notes",
)
async def read_notas(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    cita_id: int | None = None,
    current_user: UserModel = Depends(get_current_user),
) -> list[NotaMedicaOut]:
    """List of medical notes, optionally filtered by appointment."""
    return await crud_nota_medica.get_notas(db, skip=skip, limit=limit, cita_id=cita_id)


@router.post(
    "/notas/",
    response_model=NotaMedicaOut,
    status_code=201,
    summary="Create a medical note",
    responses={
        400: {"description": "The appointment already has a medical note."},
        404: {"description": "Appointment not found."},
    },
)
async def create_nota(
    *,
    db: AsyncSession = Depends(get_db),
    nota_in: NotaMedicaCreate,
    current_user: UserModel = Depends(get_current_user),
) -> NotaMedicaOut:
    """Creates a medical note for an appointment (one per appointment)."""
    cita = await crud_cita.get_cita(db, nota_in.cita_id)
    if not cita:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    if await crud_nota_medica.get_nota_by_cita(db, nota_in.cita_id):
        raise HTTPException(
            status_code=400, detail="The appointment already has a medical note."
        )
    try:
        return await crud_nota_medica.create_nota(db, nota=nota_in)
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="The appointment already has a medical note."
        ) from None


@router.get(
    "/notas/{nota_id}",
    response_model=NotaMedicaOut,
    summary="Get a medical note by ID",
    responses={404: {"description": "Medical note not found."}},
)
async def read_nota_by_id(
    nota_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> NotaMedicaOut:
    """Gets a medical note by ID."""
    nota = await crud_nota_medica.get_nota(db, nota_id)
    if not nota:
        raise HTTPException(status_code=404, detail="Medical note not found.")
    return nota


@router.put(
    "/notas/{nota_id}",
    response_model=NotaMedicaOut,
    summary="Update a medical note",
    responses={404: {"description": "Medical note not found."}},
)
async def update_nota(
    *,
    db: AsyncSession = Depends(get_db),
    nota_id: int,
    nota_in: NotaMedicaUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> NotaMedicaOut:
    """Updates an existing medical note."""
    db_nota = await crud_nota_medica.get_nota(db, nota_id)
    if not db_nota:
        raise HTTPException(status_code=404, detail="Medical note not found.")
    return await crud_nota_medica.update_nota(db, db_nota, nota_in)


@router.delete(
    "/notas/{nota_id}",
    response_model=NotaMedicaOut,
    summary="Delete a medical note",
    responses={404: {"description": "Medical note not found."}},
)
async def delete_nota(
    *,
    db: AsyncSession = Depends(get_db),
    nota_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> NotaMedicaOut:
    """Deletes a medical note."""
    nota = await crud_nota_medica.delete_nota(db, nota_id)
    if not nota:
        raise HTTPException(status_code=404, detail="Medical note not found.")
    return nota
