from typing import Any, Optional
import asyncio
import uuid

from dependencies import get_current_user, get_db
from dependencies_i18n import I18nResponse, get_language
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.appointment import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    MedicalNoteCreate,
    MedicalNoteOut,
    MedicalNoteUpdate,
    PaginatedResponse,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core import crud_appointment, crud_doctor, crud_medical_note, crud_patient
from core.crud_notification import create_notification
from models.user import User as UserModel

router = APIRouter(prefix="/api/v1", tags=["Appointments"])

router = APIRouter(prefix="/api/v1", tags=["Appointments"])


@router.get(
    "/appointments/",
    response_model=PaginatedResponse,
    summary="Get a paginated list of appointments",
)
async def list_appointments(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=999, description="Items per page"),
    patient_id: int | None = None,
    doctor_id: int | None = None,
    status: str | None = None,
    assistant_specialist_ids: str | None = Query(None, description="Comma-separated list of specialist IDs"),
    enrich_visuals: bool = Query(True, description="Enrich with visual indicators (delayed, proximity)"),
    current_user: UserModel = Depends(get_current_user),
) -> PaginatedResponse:
    """List of appointments with pagination, optional filters by patient, doctor, and status."""
    specialist_ids: list[uuid.UUID] | None = None
    if assistant_specialist_ids:
        try:
            specialist_ids = [uuid.UUID(s.strip()) for s in assistant_specialist_ids.split(",") if s.strip()]
        except (ValueError, AttributeError):
            specialist_ids = None
    result = await crud_appointment.get_appointments_paginated(
        db,
        page=page,
        page_size=page_size,
        patient_id=patient_id,
        doctor_id=doctor_id,
        status=status,
        user_id=current_user.id,
        assistant_specialist_ids=specialist_ids,
        enrich_visuals=enrich_visuals,
    )
    return PaginatedResponse(**result)


@router.post(
    "/appointments/",
    response_model=AppointmentOut,
    status_code=201,
    summary="Schedule a new appointment",
    responses={
        400: {"description": "Invalid data."},
        404: {"description": "Patient or doctor not found."},
        409: {"description": "The doctor already has an appointment at that time."},
    },
)
async def create_appointment(
    *,
    db: AsyncSession = Depends(get_db),
    appointment_in: AppointmentCreate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> AppointmentOut:
    """Schedules a new appointment in PENDING status."""
    i18n = I18nResponse(language)

    if not await crud_patient.get_patient(db, appointment_in.patient_id):
        raise i18n.error("patient_not_found", status_code=404)
    if not await crud_doctor.get_doctor(db, appointment_in.doctor_id):
        raise i18n.error("doctor_not_found", status_code=404)
    try:
        appt = await crud_appointment.create_appointment(
            db, appointment=appointment_in, user_id=current_user.id
        )
        doctor = await crud_doctor.get_doctor(db, appointment_in.doctor_id)
        patient = await crud_patient.get_patient(db, appointment_in.patient_id)
        dname = f"{doctor.first_name} {doctor.last_name}" if doctor else "Doctor"
        pname = f"{patient.first_name} {patient.last_name}" if patient else "Paciente"
        asyncio.create_task(
            create_notification(
                appointment_in.patient_id,
                "appointment_created",
                "Cita programada",
                f"Hola {pname}, tienes una cita con {dname} el {appt.start_datetime}.",
            )
        )
        return appt
    except ValueError as exc:
        if "at that time" in str(exc):
            raise i18n.error("appointment_already_exists", status_code=409) from exc
        raise i18n.error("bad_request", status_code=400) from exc


@router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentOut,
    summary="Get an appointment by ID",
    responses={404: {"description": "Appointment not found."}},
)
async def get_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
    enrich_visuals: bool = Query(True, description="Enrich with visual indicators"),
) -> AppointmentOut:
    """Gets an appointment by ID."""
    i18n = I18nResponse(language)
    appointment = await crud_appointment.get_appointment(
        db, appointment_id, user_id=current_user.id
    )
    if not appointment:
        raise i18n.error("appointment_not_found", status_code=404)
    
    if True:  # Always enrich single appointment
        from core.crud_visual_indicator import enrich_appointments_with_visuals
        appointments = await crud_visual_indicator.enrich_appointments_with_visuals(db, [appointment])
        return appointments[0]
    
    return appointment


@router.put(
    "/appointments/{appointment_id}",
    response_model=AppointmentOut,
    summary="Reschedule an appointment",
    responses={
        400: {"description": "Cannot reschedule or invalid data."},
        404: {"description": "Appointment not found."},
        409: {"description": "The doctor already has an appointment at that time."},
    },
)
async def update_appointment(
    *,
    db: AsyncSession = Depends(get_db),
    appointment_id: int,
    appointment_in: AppointmentUpdate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> AppointmentOut:
    """Reschedules an appointment and transitions it to RESCHEDULED status."""
    i18n = I18nResponse(language)
    db_appointment = await crud_appointment.get_appointment(
        db, appointment_id, user_id=current_user.id
    )
    if not db_appointment:
        raise i18n.error("appointment_not_found", status_code=404)
    try:
        appt = await crud_appointment.reschedule_appointment(
            db, db_appointment, appointment_in
        )
        doctor = await crud_doctor.get_doctor(db, db_appointment.doctor_id)
        patient = await crud_patient.get_patient(db, db_appointment.patient_id)
        dname = f"{doctor.first_name} {doctor.last_name}" if doctor else "Doctor"
        pname = f"{patient.first_name} {patient.last_name}" if patient else "Paciente"
        asyncio.create_task(
            create_notification(
                db_appointment.patient_id,
                "appointment_rescheduled",
                "Cita reagendada",
                f"Hola {pname}, tu cita con {dname} fue reagendada para {appt.start_datetime}.",
            )
        )
        return appt
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/appointments/{appointment_id}/status",
    response_model=AppointmentOut,
    summary="Change appointment status",
    responses={
        400: {"description": "Invalid status transition."},
        404: {"description": "Appointment not found."},
    },
)
async def change_appointment_status(
    *,
    db: AsyncSession = Depends(get_db),
    appointment_id: int,
    cambio: AppointmentStatusUpdate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> AppointmentOut:
    """Changes appointment status following valid transitions."""
    i18n = I18nResponse(language)
    db_appointment = await crud_appointment.get_appointment(
        db, appointment_id, user_id=current_user.id
    )
    if not db_appointment:
        raise i18n.error("appointment_not_found", status_code=404)
    try:
        return await crud_appointment.change_status(db, db_appointment, cambio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/appointments/{appointment_id}",
    summary="Delete an appointment",
    responses={404: {"description": "Appointment not found."}},
)
async def delete_appointment(
    *,
    db: AsyncSession = Depends(get_db),
    appointment_id: int,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> dict[str, str]:
    """Deletes an appointment."""
    i18n = I18nResponse(language)
    db_appointment = await crud_appointment.get_appointment(
        db, appointment_id, user_id=current_user.id
    )
    if not db_appointment:
        raise i18n.error("appointment_not_found", status_code=404)
    await crud_appointment.delete_appointment(db, db_appointment)
    return {"detail": i18n.get("appointment_deleted")}


# ---------- Medical notes ----------
@router.get(
    "/notes/",
    response_model=list[MedicalNoteOut],
    summary="Get medical notes",
)
async def list_notes(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    appointment_id: int | None = None,
    current_user: UserModel = Depends(get_current_user),
) -> list[MedicalNoteOut]:
    """List of medical notes, optionally filtered by appointment."""
    return await crud_medical_note.get_notes(
        db, skip=skip, limit=limit, appointment_id=appointment_id
    )


@router.post(
    "/notes/",
    response_model=MedicalNoteOut,
    status_code=201,
    summary="Create a medical note",
    responses={
        400: {"description": "The appointment already has a medical note."},
        404: {"description": "Appointment not found."},
    },
)
async def create_note(
    *,
    db: AsyncSession = Depends(get_db),
    note_in: MedicalNoteCreate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> MedicalNoteOut:
    """Creates a medical note for an appointment (one per appointment)."""
    i18n = I18nResponse(language)
    appointment = await crud_appointment.get_appointment(db, note_in.appointment_id)
    if not appointment:
        raise i18n.error("appointment_not_found", status_code=404)
    if await crud_medical_note.get_note_by_appointment(db, note_in.appointment_id):
        raise i18n.error("note_already_exists", status_code=400)
    try:
        note = await crud_medical_note.create_note(db, note=note_in)
    except IntegrityError:
        raise i18n.error("note_already_exists", status_code=400) from None

    # Auto-ingest into vector store (fire-and-forget)
    try:
        from core.rag import ingest_document

        content_parts = [f"Diagnosis: {note_in.diagnosis}"]
        if note_in.treatment:
            content_parts.append(f"Treatment: {note_in.treatment}")
        if note_in.observations:
            content_parts.append(f"Observations: {note_in.observations}")
        await ingest_document(
            db,
            reference_type="MEDICAL_NOTE",
            reference_id=note.id,
            title=f"Medical note appointment #{note_in.appointment_id}",
            content="\n".join(content_parts),
        )
    except Exception:
        pass  # Non-blocking: log in production

    return note


@router.get(
    "/notes/{note_id}",
    response_model=MedicalNoteOut,
    summary="Get a medical note by ID",
    responses={404: {"description": "Medical note not found."}},
)
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> MedicalNoteOut:
    """Gets a medical note by ID."""
    i18n = I18nResponse(language)
    note = await crud_medical_note.get_note(db, note_id)
    if not note:
        raise i18n.error("note_not_found", status_code=404)
    return note


@router.put(
    "/notes/{note_id}",
    response_model=MedicalNoteOut,
    summary="Update a medical note",
    responses={404: {"description": "Medical note not found."}},
)
async def update_note(
    *,
    db: AsyncSession = Depends(get_db),
    note_id: int,
    note_in: MedicalNoteUpdate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> MedicalNoteOut:
    """Updates an existing medical note."""
    i18n = I18nResponse(language)
    db_note = await crud_medical_note.get_note(db, note_id)
    if not db_note:
        raise i18n.error("note_not_found", status_code=404)
    return await crud_medical_note.update_note(db, db_note, note_in)


@router.delete(
    "/notes/{note_id}",
    response_model=MedicalNoteOut,
    summary="Delete a medical note",
    responses={404: {"description": "Medical note not found."}},
)
async def delete_note(
    *,
    db: AsyncSession = Depends(get_db),
    note_id: int,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> MedicalNoteOut:
    """Deletes a medical note."""
    i18n = I18nResponse(language)
    note = await crud_medical_note.delete_note(db, note_id)
    if not note:
        raise i18n.error("note_not_found", status_code=404)
    return note
