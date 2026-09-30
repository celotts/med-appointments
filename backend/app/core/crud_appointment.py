from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from core import crud_appointment_audit, crud_audit
from core.crud_notification import create_notification
from core.crud_visual_indicator import (
    STATUSES_THAT_OCCUPY,
    TERMINAL_STATUSES,
)
from models.appointment import Appointment as AppointmentModel
from models.appointment_status import AppointmentStatus as AppointmentStatusModel
from models.doctor import Doctor
from models.patient import Patient
from models.user import User as UserModel
from schemas.appointment import (
    AppointmentCreate as AppointmentCreateSchema,
)
from schemas.appointment import (
    AppointmentStatusCode,
    AppointmentStatusUpdate,
)
from schemas.appointment import (
    AppointmentUpdate as AppointmentUpdateSchema,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Statuses that block the doctor's schedule (prevent booking in that slot)
_STATUSES_THAT_OCCUPY = STATUSES_THAT_OCCUPY

# Terminal statuses: cannot reschedule or change from here
_TERMINAL_STATUSES = TERMINAL_STATUSES


async def get_status_by_code(db: AsyncSession, code: str | AppointmentStatusCode) -> object | None:
    result = await db.execute(
        select(AppointmentStatusModel).where(AppointmentStatusModel.code == code)
    )
    return result.scalars().first()


async def get_status_by_id(db: AsyncSession, status_id: int):
    return await db.get(AppointmentStatusModel, status_id)


async def get_appointment(
    db: AsyncSession, appointment_id: int, user_id: str | None = None
) -> AppointmentModel | None:
    """Get a appointment by its ID."""
    stmt = select(AppointmentModel).filter(AppointmentModel.id == appointment_id)
    if user_id is not None:
        stmt = stmt.where(AppointmentModel.user_id == user_id)
    result = await db.execute(stmt.options(selectinload(AppointmentModel.status)))
    return result.scalars().first()


async def get_appointments(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    patient_id: int | None = None,
    doctor_id: int | None = None,
    status: str | None = None,
    user_id: str | None = None,
    enrich_visuals: bool = True,
) -> list[AppointmentModel]:
    stmt = (
        select(AppointmentModel)
        .options(selectinload(AppointmentModel.status))
        .order_by(AppointmentModel.start_datetime.desc())
    )
    if patient_id is not None:
        stmt = stmt.where(AppointmentModel.patient_id == patient_id)
    if doctor_id is not None:
        stmt = stmt.where(AppointmentModel.doctor_id == doctor_id)
    if status is not None:
        sub = select(AppointmentStatusModel.id).where(
            AppointmentStatusModel.code == status
        )
        stmt = stmt.where(AppointmentModel.status_id.in_(sub))
    if user_id is not None:
        stmt = stmt.where(AppointmentModel.user_id == user_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    appointments = result.scalars().all()

    # Enriquecer con indicadores visuales si se solicita
    if enrich_visuals and appointments:
        from core.crud_visual_indicator import enrich_appointments_with_visuals
        appointments = await enrich_appointments_with_visuals(db, list(appointments))

    return list(appointments)


async def get_appointments_paginated(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    patient_id: int | None = None,
    doctor_id: int | None = None,
    status: str | None = None,
    user_id: str | None = None,
    assistant_specialist_ids: list[uuid.UUID] | None = None,
    enrich_visuals: bool = True,
) -> dict:
    """Get appointments with pagination info (items + total count)."""
    skip = (page - 1) * page_size

    base_stmt = select(AppointmentModel)
    if patient_id is not None:
        base_stmt = base_stmt.where(AppointmentModel.patient_id == patient_id)
    if doctor_id is not None:
        base_stmt = base_stmt.where(AppointmentModel.doctor_id == doctor_id)
    if assistant_specialist_ids:
        base_stmt = base_stmt.where(AppointmentModel.doctor_id.in_(assistant_specialist_ids))
    if status is not None:
        sub = select(AppointmentStatusModel.id).where(
            AppointmentStatusModel.code == status
        )
        base_stmt = base_stmt.where(AppointmentModel.status_id.in_(sub))
    if user_id is not None:
        base_stmt = base_stmt.where(AppointmentModel.user_id == user_id)

    # Get total count
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get paginated items
    items_stmt = (
        base_stmt
        .options(selectinload(AppointmentModel.status))
        .order_by(AppointmentModel.start_datetime.desc())
        .offset(skip)
        .limit(page_size)
    )
    items_result = await db.execute(items_stmt)
    appointments = items_result.scalars().all()

    # Enriquecer con indicadores visuales si se solicita
    if enrich_visuals and appointments:
        from core.crud_visual_indicator import enrich_appointments_with_visuals
        appointments = await enrich_appointments_with_visuals(db, list(appointments))

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "items": list(appointments),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def _has_conflict(
    db: AsyncSession,
    *,
    doctor_id: int,
    start: datetime,
    end: datetime,
    exclude_appointment_id: int | None = None,
) -> bool:
    """Check if a doctor already has an overlapping appointment in [start, end)."""
    statuses_that_occupy = select(AppointmentStatusModel.id).where(
        AppointmentStatusModel.code.in_(_STATUSES_THAT_OCCUPY)
    )
    stmt = select(AppointmentModel.id).where(
        AppointmentModel.doctor_id == doctor_id,
        AppointmentModel.status_id.in_(statuses_that_occupy),
        AppointmentModel.start_datetime < end,
        AppointmentModel.end_datetime > start,
    )
    if exclude_appointment_id is not None:
        stmt = stmt.where(AppointmentModel.id != exclude_appointment_id)
    result = await db.execute(stmt.limit(1))
    return result.scalars().first() is not None


async def create_appointment(
    db: AsyncSession, appointment: AppointmentCreateSchema, user_id: str
) -> AppointmentModel:
    if appointment.end_datetime <= appointment.start_datetime:
        raise ValueError("end_datetime must be after start_datetime")
    if await _has_conflict(
        db,
        doctor_id=appointment.doctor_id,
        start=appointment.start_datetime,
        end=appointment.end_datetime,
    ):
        raise ValueError("The doctor already has an appointment at that time.")

    db_status = await get_status_by_code(db, AppointmentStatusCode.PENDING)
    if db_status is None:
        raise ValueError("PENDING status does not exist. Run the status seed.")

    db_appointment = AppointmentModel(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        user_id=user_id,
        status_id=db_status.id,
        start_datetime=appointment.start_datetime,
        end_datetime=appointment.end_datetime,
        reason=appointment.reason,
    )
    db.add(db_appointment)
    await db.flush()  # necesitamos el id para el registro de auditoria

    # Auditoria: `from_state=None` porque la cita no existia antes.
    await crud_appointment_audit.registrar_creacion(
        db, db_appointment, actor=db_appointment_user(db_appointment)
    )

    await db.commit()
    await db.refresh(db_appointment)
    return await get_appointment(db, db_appointment.id, user_id=user_id)


def db_appointment_user(appointment: AppointmentModel) -> UserModel | None:
    """El usuario que creo la cita, si la columna `user_id` lo referencia.

    `appointments.user_id` apunta a `users.id`; devuelve un stub con el id
    porque en este punto no hace falta cargar el usuario completo.
    """
    if appointment.user_id is None:
        return None
    stub = UserModel()
    stub.id = appointment.user_id
    return stub


async def reschedule_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    appointment: AppointmentUpdateSchema,
    *,
    new_status: bool = True,
    actor: UserModel | None = None,
) -> AppointmentModel:
    """Reschedule an appointment to a new time slot and mark as RESCHEDULED."""
    from core.crud_visual_indicator import TERMINAL_STATUSES
    if db_appointment.status.code in TERMINAL_STATUSES:
        raise ValueError("Cannot reschedule a cancelled or attended appointment.")

    # Se captura el estado y el actor ANTES de tocar nada. Tras el flush de la
    # auditoria la sesion queda expirada, y leer `db_appointment.status` o
    # `current_user.id` despues lanzaria MissingGreenlet.
    estado_anterior = db_appointment.status.code
    actor_id = getattr(actor, "id", None)

    new_start = appointment.start_datetime or db_appointment.start_datetime
    new_end = appointment.end_datetime or db_appointment.end_datetime
    if new_end <= new_start:
        raise ValueError("end_datetime must be after start_datetime")

    if await _has_conflict(
        db,
        doctor_id=db_appointment.doctor_id,
        start=new_start,
        end=new_end,
        exclude_appointment_id=db_appointment.id,
    ):
        raise ValueError("The doctor already has an appointment at that time.")

    db_appointment.start_datetime = new_start
    db_appointment.end_datetime = new_end
    if appointment.reason:
        db_appointment.reason = appointment.reason

    if new_status:
        status = await get_status_by_code(db, AppointmentStatusCode.RESCHEDULED)
        if status is None:
            raise ValueError("RESCHEDULED status does not exist.")
        db_appointment.status_id = status.id

    # El reagendamiento cambia estado y horario: se audita como transicion.
    await crud_audit.registrar_transicion_cita(
        db,
        appointment_id=db_appointment.id,
        from_state=estado_anterior,
        to_state=db_appointment.status.code,
        user_id=actor_id,
        reason="Reagendada",
        metadata={
            "start_datetime": new_start.isoformat(),
            "end_datetime": new_end.isoformat(),
        },
    )

    await db.commit()
    await db.refresh(db_appointment)
    return await get_appointment(db, db_appointment.id)


async def change_status(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    cambio: AppointmentStatusUpdate,
    *,
    actor: UserModel | None = None,
) -> AppointmentModel:
    """Transition appointment status following the state machine.

    Valida contra `VALID_TRANSITIONS` y deja registro en la auditoria.
    """
    await crud_appointment_audit.transicionar(
        db, db_appointment, cambio.status, actor=actor, reason="Cambio de estado (PATCH /status)"
    )
    return await get_appointment(db, db_appointment.id)


# --- New specific transition functions ---

async def confirm_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    current_user: UserModel,
) -> AppointmentModel:
    """Confirm a PENDING appointment. Can be done by patient, doctor, or staff."""
    if db_appointment.status.code != "PENDIENTE":
        raise ValueError("Only PENDING appointments can be confirmed.")

    await crud_appointment_audit.transicionar(
        db,
        db_appointment,
        AppointmentStatusCode.CONFIRMED,
        actor=current_user,
        reason="Confirmada por el paciente o por secretaria",
    )

    # Notify patient
    patient = await db.get(Patient, db_appointment.patient_id)
    doctor = await db.get(Doctor, db_appointment.doctor_id)
    if patient and doctor:
        asyncio.create_task(
            create_notification(
                patient.id,
                "appointment_confirmed",
                "Cita confirmada",
                f"Hola {patient.first_name}, tu cita con {doctor.first_name} {doctor.last_name} del {db_appointment.start_datetime.strftime('%d/%m/%Y %H:%M')} ha sido confirmada.",
            )
        )

    return await get_appointment(db, db_appointment.id)


async def attend_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    current_user: UserModel,
    notes: str | None = None,
    duration_minutes: int | None = None,
) -> AppointmentModel:
    """Mark appointment as ATTENDED. Only doctors can do this. Must come from IN_PROGRESS."""
    if db_appointment.status.code not in ("EN PROCESO",):
        raise ValueError("Only appointments IN PROGRESS can be marked as attended.")

    # Check tolerance: appointment should have started (or be within 30 min after end)
    now = datetime.now(timezone.utc)
    if now < db_appointment.start_datetime - timedelta(minutes=30):
        raise ValueError("Cannot attend appointment before its start time.")

    # Tolerancia de +/-30 min. Si se atiende tarde, queda en la auditoria: el
    # comentario original decia "log for audit" pero no se implemento.
    metadata: dict = {}
    if now > db_appointment.end_datetime + timedelta(minutes=30):
        metadata["atencion_tardia_min"] = int(
            (now - db_appointment.end_datetime).total_seconds() // 60
        )
    if duration_minutes:
        metadata["duration_min"] = duration_minutes

    await crud_appointment_audit.transicionar(
        db,
        db_appointment,
        AppointmentStatusCode.ATTENDED,
        actor=current_user,
        reason=notes or "Consulta completada",
        metadata=metadata or None,
    )

    # Create medical note if provided
    if notes or duration_minutes:
        from core import crud_medical_note
        from schemas.appointment import MedicalNoteCreate
        note_in = MedicalNoteCreate(
            appointment_id=db_appointment.id,
            diagnosis=notes or "Consulta médica",
            treatment="",
            observations=notes or "",
        )
        await crud_medical_note.create_note(db, note_in, actor=current_user)

    await db.commit()
    await db.refresh(db_appointment)
    return await get_appointment(db, db_appointment.id)


async def wait_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    current_user: UserModel,
) -> AppointmentModel:
    """Mark appointment as WAITING (EN ESPERA). Patient has arrived at clinic."""
    if db_appointment.status.code not in ("CONFIRMADA", "REAGENDADA"):
        raise ValueError("Only CONFIRMED or RESCHEDULED appointments can be moved to waiting.")

    await crud_appointment_audit.transicionar(
        db,
        db_appointment,
        AppointmentStatusCode.WAITING,
        actor=current_user,
        reason="El paciente llego a la clinica",
    )
    return await get_appointment(db, db_appointment.id)


async def start_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    current_user: UserModel,
) -> AppointmentModel:
    """Mark appointment as IN PROGRESS (EN PROCESO). Patient called to consultation."""
    if db_appointment.status.code != "EN ESPERA":
        raise ValueError("Only appointments in WAITING can be started.")

    await crud_appointment_audit.transicionar(
        db,
        db_appointment,
        AppointmentStatusCode.IN_PROGRESS,
        actor=current_user,
        reason="Consulta iniciada",
    )
    return await get_appointment(db, db_appointment.id)


async def suspend_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    current_user: UserModel,
    reason: str,
) -> AppointmentModel:
    """Suspend an appointment. Can be done by doctor or staff. Reason is required."""
    if db_appointment.status.code in ("ATENDIDA", "CANCELADA"):
        raise ValueError("Cannot suspend an attended or cancelled appointment.")

    if not reason or not reason.strip():
        raise ValueError("El motivo de suspensión es obligatorio.")

    db_appointment.reason = f"{db_appointment.reason}\n[Suspendida]: {reason.strip()}"

    await crud_appointment_audit.transicionar(
        db,
        db_appointment,
        AppointmentStatusCode.SUSPENDED,
        actor=current_user,
        reason=reason.strip(),
    )

    # Notify patient
    patient = await db.get(Patient, db_appointment.patient_id)
    doctor = await db.get(Doctor, db_appointment.doctor_id)
    if patient and doctor:
        asyncio.create_task(
            create_notification(
                patient.id,
                "appointment_suspended",
                "Cita suspendida",
                f"Hola {patient.first_name}, tu cita con {doctor.first_name} {doctor.last_name} ha sido suspendida. Motivo: {reason.strip()}.",
            )
        )

    return await get_appointment(db, db_appointment.id)


async def cancel_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    current_user: UserModel,
    reason: str,
) -> AppointmentModel:
    """Cancel an appointment. Can be done by patient or staff. Reason is required."""
    if db_appointment.status.code in ("ATENDIDA", "CANCELADA"):
        raise ValueError("Cannot cancel an attended or already cancelled appointment.")

    if not reason or not reason.strip():
        raise ValueError("El motivo de cancelación es obligatorio.")

    # Check if appointment is in the past
    if db_appointment.start_datetime < datetime.now(timezone.utc):
        raise ValueError("Cannot cancel a past appointment. Use suspend instead.")

    db_appointment.reason = f"{db_appointment.reason}\n[Cancelada]: {reason.strip()}"

    await crud_appointment_audit.transicionar(
        db,
        db_appointment,
        AppointmentStatusCode.CANCELLED,
        actor=current_user,
        reason=reason.strip(),
    )

    # Notify patient and doctor
    patient = await db.get(Patient, db_appointment.patient_id)
    doctor = await db.get(Doctor, db_appointment.doctor_id)
    if patient and doctor:
        asyncio.create_task(
            create_notification(
                patient.id,
                "appointment_cancelled",
                "Cita cancelada",
                f"Hola {patient.first_name}, tu cita con {doctor.first_name} {doctor.last_name} del {db_appointment.start_datetime.strftime('%d/%m/%Y %H:%M')} ha sido cancelada. Motivo: {reason.strip()}.",
            )
        )

    return await get_appointment(db, db_appointment.id)


async def reactivate_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    current_user: UserModel,
) -> AppointmentModel:
    """Reactivate a CANCELLED appointment back to PENDING. Only if date is in future."""
    if db_appointment.status.code != "CANCELADA":
        raise ValueError("Only cancelled appointments can be reactivated.")

    # Check if appointment date is in the future
    if db_appointment.start_datetime <= datetime.now(timezone.utc):
        raise ValueError("Cannot reactivate a past appointment.")

    await crud_appointment_audit.transicionar(
        db,
        db_appointment,
        AppointmentStatusCode.PENDING,
        actor=current_user,
        reason="Reactivada desde CANCELADA",
    )

    # Notify patient
    patient = await db.get(Patient, db_appointment.patient_id)
    doctor = await db.get(Doctor, db_appointment.doctor_id)
    if patient and doctor:
        asyncio.create_task(
            create_notification(
                patient.id,
                "appointment_reactivated",
                "Cita reactivada",
                f"Hola {patient.first_name}, tu cita con {doctor.first_name} {doctor.last_name} del {db_appointment.start_datetime.strftime('%d/%m/%Y %H:%M')} ha sido reactivada.",
            )
        )

    return await get_appointment(db, db_appointment.id)


async def update_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    appointment: AppointmentUpdateSchema,
    *,
    actor: UserModel | None = None,
) -> AppointmentModel:
    # Check if appointment is in a terminal state (cannot be modified)
    from core.crud_visual_indicator import TERMINAL_STATUSES
    if db_appointment.status.code in TERMINAL_STATUSES:
        raise ValueError(f"Cannot modify appointment in {db_appointment.status.code} state.")

    if appointment.start_datetime is not None or appointment.end_datetime is not None:
        new_start = appointment.start_datetime or db_appointment.start_datetime
        new_end = appointment.end_datetime or db_appointment.end_datetime
        if new_end <= new_start:
            raise ValueError("end_datetime must be after start_datetime")
        if await _has_conflict(
            db,
            doctor_id=db_appointment.doctor_id,
            start=new_start,
            end=new_end,
            exclude_appointment_id=db_appointment.id,
        ):
            raise ValueError("The doctor already has an appointment at that time.")

    data = appointment.model_dump(exclude_unset=True)
    # Valores previos para la auditoria: sin esto el registro solo diria
    # "algo cambio", que es inutil para una investigacion posterior.
    valores_previos = {
        campo: getattr(db_appointment, campo, None) for campo in data
    }
    for field, value in data.items():
        setattr(db_appointment, field, value)

    await crud_appointment_audit.registrar_actualizacion(
        db,
        db_appointment,
        campos=data,
        valores_previos=valores_previos,
        actor=actor,
    )

    await db.commit()
    await db.refresh(db_appointment)
    return await get_appointment(db, db_appointment.id)


async def delete_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    *,
    actor: UserModel | None = None,
) -> AppointmentModel:
    # El registro se escribe en la misma transaccion que el DELETE, para que
    # el rastro sobreviva al registro que describe.
    await crud_appointment_audit.registrar_borrado(db, db_appointment, actor=actor)
    await db.delete(db_appointment)
    await db.commit()
    return db_appointment


async def get_statuses(db: AsyncSession) -> list:
    result = await db.execute(
        select(AppointmentStatusModel).order_by(AppointmentStatusModel.id)
    )
    return result.scalars().all()


# --- CRUD for Appointment Statuses ---

async def create_status(
    db: AsyncSession, code: str, description: str | None = None
) -> AppointmentStatusModel:
    """Create a new appointment status."""
    existing = await get_status_by_code(db, code)
    if existing:
        raise ValueError(f"Status with code '{code}' already exists.")

    status = AppointmentStatusModel(code=code, description=description)
    db.add(status)
    await db.commit()
    await db.refresh(status)
    return status


async def update_status(
    db: AsyncSession, status_id: int, code: str | None = None, description: str | None = None
) -> AppointmentStatusModel:
    """Update an existing appointment status."""
    status = await get_status_by_id(db, status_id)
    if not status:
        raise ValueError(f"Status with id {status_id} not found.")

    if code is not None:
        existing = await get_status_by_code(db, code)
        if existing and existing.id != status_id:
            raise ValueError(f"Status with code '{code}' already exists.")
        status.code = code

    if description is not None:
        status.description = description

    await db.commit()
    await db.refresh(status)
    return status


async def delete_status(db: AsyncSession, status_id: int) -> bool:
    """Delete an appointment status. Returns True if deleted, False if not found."""
    status = await get_status_by_id(db, status_id)
    if not status:
        return False

    # Check if status is being used by any appointment
    from sqlalchemy import func, select
    count_result = await db.execute(
        select(func.count(AppointmentModel.id)).where(AppointmentModel.status_id == status_id)
    )
    count = count_result.scalar() or 0
    if count > 0:
        raise ValueError(f"Cannot delete status '{status.code}' - it is used by {count} appointment(s).")

    await db.delete(status)
    await db.commit()
    return True


# --- Batch job: Auto-cancel no-show appointments ---
async def auto_cancel_no_show_appointments(db: AsyncSession) -> int:
    """
    Batch job to auto-cancel appointments that were scheduled for previous days
    but were never attended. Runs daily at 02:00.
    """
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Find appointments that:
    # - Status is PENDIENTE, CONFIRMADA, or REAGENDADA
    # - Start datetime is before start of today (i.e., yesterday or earlier)
    # - No medical note exists (not attended)
    from core import crud_medical_note

    status_codes = ("PENDIENTE", "CONFIRMADA", "REAGENDADA")
    sub = select(AppointmentStatusModel.id).where(
        AppointmentStatusModel.code.in_(status_codes)
    )

    stmt = select(AppointmentModel).where(
        AppointmentModel.status_id.in_(sub),
        AppointmentModel.start_datetime < start_of_today,
    )

    result = await db.execute(stmt.options(selectinload(AppointmentModel.status)))
    appointments = result.scalars().all()

    cancelled_count = 0
    for appt in appointments:
        # Check if there's a medical note (meaning it was attended)
        medical_note = await crud_medical_note.get_note_by_appointment(db, appt.id)
        if medical_note:
            continue  # Was attended, skip

        # Datos del actor antes de auditar: tras el flush la sesion expira.
        appointment_id = appt.id
        estado_anterior = appt.status.code
        patient_id = appt.patient_id
        doctor_id = appt.doctor_id
        inicio = appt.start_datetime

        status = await get_status_by_code(db, AppointmentStatusCode.CANCELLED)
        if status:
            appt.status_id = status.id
            appt.reason = f"{appt.reason}\n[Auto-cancelada]: No-show detectado el {now.strftime('%d/%m/%Y')}."
            cancelled_count += 1

            # El job automatico tambien deja rastro: una cancelacion
            # automatica sin auditoria seria indistinguible de una manual.
            await crud_audit.registrar_transicion_cita(
                db,
                appointment_id=appointment_id,
                from_state=estado_anterior,
                to_state=AppointmentStatusCode.CANCELLED.value,
                user_id=None,
                reason=f"Auto-cancelada por no-show ({now.isoformat()})",
                metadata={"automatica": True, "job": "auto_cancel_no_show"},
            )

            # Notify patient
            patient = await db.get(Patient, patient_id)
            doctor = await db.get(Doctor, doctor_id)
            if patient and doctor:
                inicio_texto = inicio.strftime('%d/%m/%Y %H:%M') if inicio else ""
                pnombre, dnombre = patient.first_name, f"{doctor.first_name} {doctor.last_name}"
                asyncio.create_task(
                    create_notification(
                        patient.id,
                        "appointment_auto_cancelled",
                        "Cita auto-cancelada por no-show",
                        f"Hola {pnombre}, tu cita con {dnombre} del {inicio_texto} fue cancelada automáticamente por no asistir.",
                    )
                )

    if cancelled_count > 0:
        await db.commit()

    return cancelled_count


# --- AI Bulk Reschedule for Specialist ---
async def ai_bulk_reschedule(
    db: AsyncSession,
    doctor_id: int,
    target_date: datetime,
    criteria: str = "earliest_first",
) -> dict:
    """
    AI-powered bulk reschedule for a specialist's day.
    Finds all appointments for the doctor on target_date and reassigns them to available slots.
    """
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Get all appointments for this doctor on this date in states that can be rescheduled
    reschedulable_codes = ("PENDIENTE", "CONFIRMADA", "REAGENDADA", "SUSPENDIDA")
    sub = select(AppointmentStatusModel.id).where(
        AppointmentStatusModel.code.in_(reschedulable_codes)
    )

    stmt = select(AppointmentModel).where(
        AppointmentModel.doctor_id == doctor_id,
        AppointmentModel.status_id.in_(sub),
        AppointmentModel.start_datetime >= start_of_day,
        AppointmentModel.start_datetime <= end_of_day,
    ).order_by(AppointmentModel.start_datetime)

    result = await db.execute(stmt.options(selectinload(AppointmentModel.status)))
    appointments = result.scalars().all()

    if not appointments:
        return {"rescheduled": 0, "appointments": []}

    # Find available slots for the day (9:00 - 17:00)
    from core.crud_visual_indicator import STATUSES_THAT_OCCUPY

    # Get existing occupied slots (excluding the ones we're moving)
    appointment_ids = [a.id for a in appointments]
    occupied_stmt = select(AppointmentModel).where(
        AppointmentModel.doctor_id == doctor_id,
        AppointmentModel.start_datetime >= start_of_day,
        AppointmentModel.start_datetime <= end_of_day,
        AppointmentModel.status_id.in_(
            select(AppointmentStatusModel.id).where(
                AppointmentStatusModel.code.in_(STATUSES_THAT_OCCUPY)
            )
        ),
        AppointmentModel.id.notin_(appointment_ids),
    )
    occupied_result = await db.execute(occupied_stmt)
    occupied = occupied_result.scalars().all()

    # Build available slots (30 min increments from 9:00 to 17:00)
    day_start = target_date.replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    day_end = target_date.replace(hour=17, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

    all_slots = []
    current = day_start
    slot_duration = timedelta(minutes=30)
    while current + slot_duration <= day_end:
        all_slots.append(current)
        current += slot_duration

    # Remove occupied slots
    occupied_ranges = [(a.start_datetime, a.end_datetime) for a in occupied]
    free_slots = []
    for slot in all_slots:
        slot_end = slot + slot_duration
        is_free = True
        for occ_start, occ_end in occupied_ranges:
            if slot < occ_end and slot_end > occ_start:
                is_free = False
                break
        if is_free:
            free_slots.append(slot)

    # Sort appointments by criteria
    if criteria == "earliest_first":
        appointments.sort(key=lambda a: a.start_datetime)
    elif criteria == "priority":
        # Priority: PENDING first, then CONFIRMED, then RESCHEDULED, then SUSPENDED
        priority = {"PENDIENTE": 0, "CONFIRMADA": 1, "REAGENDADA": 2, "SUSPENDIDA": 3}
        appointments.sort(key=lambda a: (priority.get(a.status.code, 99), a.start_datetime))

    # Assign appointments to free slots
    rescheduled = []
    for appt in appointments:
        if not free_slots:
            break
        new_start = free_slots.pop(0)
        new_end = new_start + timedelta(minutes=30)

        old_start = appt.start_datetime
        appt.start_datetime = new_start
        appt.end_datetime = new_end

        # Auto-confirm after reschedule
        status = await get_status_by_code(db, AppointmentStatusCode.CONFIRMED)
        if status:
            appt.status_id = status.id

        rescheduled.append({
            "appointment_id": appt.id,
            "old_start": old_start.isoformat(),
            "new_start": new_start.isoformat(),
            "new_end": new_end.isoformat(),
        })

        # Notify patient
        patient = await db.get(Patient, appt.patient_id)
        doctor = await db.get(Doctor, appt.doctor_id)
        if patient and doctor:
            asyncio.create_task(
                create_notification(
                    patient.id,
                    "appointment_bulk_rescheduled",
                    "Cita reprogramada (reagenda masiva)",
                    f"Hola {patient.first_name}, tu cita con {doctor.first_name} {doctor.last_name} fue reprogramada de {old_start.strftime('%d/%m/%Y %H:%M')} a {new_start.strftime('%d/%m/%Y %H:%M')}.",
                )
            )

    if rescheduled:
        await db.commit()

    return {
        "rescheduled": len(rescheduled),
        "total_found": len(appointments),
        "appointments": rescheduled,
    }
