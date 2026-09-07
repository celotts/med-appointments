from datetime import datetime

from models.appointment import Appointment as AppointmentModel
from models.appointment_status import AppointmentStatus as AppointmentStatusModel
from schemas.appointment import (
    VALID_TRANSITIONS,
    AppointmentStatusCode,
    AppointmentStatusUpdate,
)
from schemas.appointment import (
    AppointmentCreate as AppointmentCreateSchema,
)
from schemas.appointment import (
    AppointmentUpdate as AppointmentUpdateSchema,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Statuses that block the doctor's schedule (prevent booking in that slot)
_STATUSES_THAT_OCCUPY = (
    AppointmentStatusCode.PENDING.value,
    AppointmentStatusCode.CONFIRMED.value,
    AppointmentStatusCode.RESCHEDULED.value,
)

# Terminal statuses: cannot reschedule or change from here
_TERMINAL_STATUSES = (
    AppointmentStatusCode.CANCELLED.value,
    AppointmentStatusCode.COMPLETED.value,
)


async def get_status_by_code(
    db: AsyncSession, code: str | AppointmentStatusCode
) -> AppointmentStatusModel | None:
    value = code.value if isinstance(code, AppointmentStatusCode) else code
    result = await db.execute(
        select(AppointmentStatusModel).filter(AppointmentStatusModel.code == value)
    )
    return result.scalars().first()


async def get_status_by_id(
    db: AsyncSession, status_id: int
) -> AppointmentStatusModel | None:
    return await db.get(AppointmentStatusModel, status_id)


async def get_statuses(db: AsyncSession) -> list[AppointmentStatusModel]:
    result = await db.execute(
        select(AppointmentStatusModel).order_by(AppointmentStatusModel.id)
    )
    return result.scalars().all()


async def get_appointment(
    db: AsyncSession, appointment_id: int
) -> AppointmentModel | None:
    result = await db.execute(
        select(AppointmentModel)
        .options(selectinload(AppointmentModel.status))
        .where(AppointmentModel.id == appointment_id)
    )
    return result.scalars().first()


async def get_appointments(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    patient_id: int | None = None,
    doctor_id: int | None = None,
    status: str | None = None,
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
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


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
    db: AsyncSession, appointment: AppointmentCreateSchema
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
        status_id=db_status.id,
        start_datetime=appointment.start_datetime,
        end_datetime=appointment.end_datetime,
        reason=appointment.reason,
    )
    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)
    return await get_appointment(db, db_appointment.id)


async def reschedule_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    appointment: AppointmentUpdateSchema,
    *,
    new_status: bool = True,
) -> AppointmentModel:
    """Reschedule an appointment to a new time slot and mark as RESCHEDULED."""
    if db_appointment.status.code in _TERMINAL_STATUSES:
        raise ValueError("Cannot reschedule a cancelled or completed appointment.")

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

    await db.commit()
    await db.refresh(db_appointment)
    return await get_appointment(db, db_appointment.id)


async def change_status(
    db: AsyncSession, db_appointment: AppointmentModel, cambio: AppointmentStatusUpdate
) -> AppointmentModel:
    """Transition appointment status following the state machine."""
    actual = AppointmentStatusCode(db_appointment.status.code)
    allowed = VALID_TRANSITIONS.get(actual, set())
    if cambio.status not in allowed:
        raise ValueError(
            f"Invalid transition from {actual.value} to {cambio.status.value}."
        )

    destination = await get_status_by_code(db, cambio.status)
    if destination is None:
        raise ValueError(f"Status {cambio.status.value} does not exist.")
    db_appointment.status_id = destination.id
    await db.commit()
    await db.refresh(db_appointment)
    return await get_appointment(db, db_appointment.id)


async def update_appointment(
    db: AsyncSession,
    db_appointment: AppointmentModel,
    appointment: AppointmentUpdateSchema,
) -> AppointmentModel:
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
    for field, value in data.items():
        setattr(db_appointment, field, value)
    await db.commit()
    await db.refresh(db_appointment)
    return await get_appointment(db, db_appointment.id)


async def delete_appointment(
    db: AsyncSession, db_appointment: AppointmentModel
) -> AppointmentModel:
    await db.delete(db_appointment)
    await db.commit()
    return db_appointment
