from datetime import datetime, timedelta

from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException
from models.appointment import Appointment
from models.user import User as UserModel
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter(prefix="/api/v1/medasist", tags=["Medasist IA"])


# ─── Schemas ──────────────────────────────────────────────────────────────
class RescheduleRequest(BaseModel):
    appointment_id: int
    preferred_date: str  # YYYY-MM-DD


class RescheduleSuggestion(BaseModel):
    start: str
    end: str
    score: float


class RescheduleResponse(BaseModel):
    appointment_id: int
    current_start: str
    current_end: str
    suggestions: list[RescheduleSuggestion]
    message: str


class AvailabilityRequest(BaseModel):
    doctor_id: int
    date: str  # YYYY-MM-DD
    duration_minutes: int = 30


class AvailabilitySlot(BaseModel):
    start: str
    end: str


class ConflictCheckRequest(BaseModel):
    doctor_id: int
    start_datetime: str
    end_datetime: str
    exclude_appointment_id: int | None = None


class ConflictCheckResponse(BaseModel):
    has_conflict: bool
    conflict_details: str | None = None
    suggested_fix: str | None = None


class FollowUpRequest(BaseModel):
    patient_id: int
    doctor_id: int
    last_appointment_date: str
    visit_type: str  # control, urgent, routine, surgery_followup


class FollowUpResponse(BaseModel):
    recommended_days: int
    recommended_date: str
    reason: str


# ─── Helper ───────────────────────────────────────────────────────────────
async def _find_free_slots(
    db: AsyncSession,
    doctor_id: int,
    target_date: datetime,
    duration_minutes: int,
) -> list[AvailabilitySlot]:
    day_start = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
    day_end = target_date.replace(hour=17, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.start_datetime >= day_start,
            Appointment.start_datetime <= day_end,
        )
    )
    existing = list(result.scalars().all())

    occupied = [
        {"start": a.start_datetime, "end": a.end_datetime} for a in existing
    ]

    all_slots = []
    current = day_start
    while current + timedelta(minutes=duration_minutes) <= day_end:
        all_slots.append(current)
        current += timedelta(minutes=duration_minutes)

    free = []
    for slot in all_slots:
        slot_end = slot + timedelta(minutes=duration_minutes)
        is_free = True
        for occ in occupied:
            if slot < occ["end"] and slot_end > occ["start"]:
                is_free = False
                break
        if is_free:
            free.append(AvailabilitySlot(start=slot.isoformat(), end=slot_end.isoformat()))

    return free


# ─── Endpoints ────────────────────────────────────────────────────────────
@router.post("/reschedule", response_model=RescheduleResponse)
async def suggest_reschedule(
    request: RescheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    appt = await db.get(Appointment, request.appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    target_date = datetime.strptime(request.preferred_date, "%Y-%m-%d")
    duration = int((appt.end_datetime - appt.start_datetime).total_seconds() / 60)

    free_slots = await _find_free_slots(db, appt.doctor_id, target_date, duration)

    if not free_slots:
        return RescheduleResponse(
            appointment_id=appt.id,
            current_start=appt.start_datetime.isoformat(),
            current_end=appt.end_datetime.isoformat(),
            suggestions=[],
            message="No available slots on the requested date.",
        )

    original_hour = appt.start_datetime.hour
    scored = []
    for slot in free_slots:
        slot_hour = datetime.fromisoformat(slot.start).hour
        time_diff = abs(slot_hour - original_hour)
        score = max(0, 1 - (time_diff * 0.1))
        if 9 <= slot_hour <= 12:
            score += 0.1
        scored.append(RescheduleSuggestion(start=slot.start, end=slot.end, score=round(score, 2)))

    scored.sort(key=lambda s: s.score, reverse=True)

    return RescheduleResponse(
        appointment_id=appt.id,
        current_start=appt.start_datetime.isoformat(),
        current_end=appt.end_datetime.isoformat(),
        suggestions=scored[:5],
        message=f"Found {len(scored)} alternative(s).",
    )


@router.post("/check-conflict", response_model=ConflictCheckResponse)
async def check_conflict(
    request: ConflictCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    proposed_start = datetime.fromisoformat(request.start_datetime)
    proposed_end = datetime.fromisoformat(request.end_datetime)

    query = select(Appointment).where(
        Appointment.doctor_id == request.doctor_id,
        Appointment.start_datetime < proposed_end,
        Appointment.end_datetime > proposed_start,
    )
    if request.exclude_appointment_id:
        query = query.where(Appointment.id != request.exclude_appointment_id)

    result = await db.execute(query)
    conflicts = list(result.scalars().all())

    if not conflicts:
        return ConflictCheckResponse(has_conflict=False)

    conflict = conflicts[0]
    return ConflictCheckResponse(
        has_conflict=True,
        conflict_details=f"Overlaps with appointment #{conflict.id} ({conflict.start_datetime.strftime('%H:%M')} - {conflict.end_datetime.strftime('%H:%M')})",
        suggested_fix="Try shifting 30 minutes later or choosing a different day.",
    )


@router.post("/available-slots", response_model=list[AvailabilitySlot])
async def get_available_slots(
    request: AvailabilityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    target_date = datetime.strptime(request.date, "%Y-%m-%d")
    return await _find_free_slots(db, request.doctor_id, target_date, request.duration_minutes)


FOLLOW_UP_RULES = {
    "control": {"days": 30, "reason": "Routine control visit"},
    "urgent": {"days": 7, "reason": "Follow-up after urgent visit"},
    "routine": {"days": 90, "reason": "Routine checkup"},
    "surgery_followup": {"days": 14, "reason": "Post-surgery follow-up"},
}


@router.post("/suggest-followup", response_model=FollowUpResponse)
async def suggest_followup(
    request: FollowUpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    rule = FOLLOW_UP_RULES.get(request.visit_type)
    if not rule:
        raise HTTPException(status_code=400, detail="Invalid visit type")

    last_date = datetime.strptime(request.last_appointment_date, "%Y-%m-%d")
    recommended = last_date + timedelta(days=rule["days"])

    if recommended.weekday() == 5:
        recommended += timedelta(days=2)
    elif recommended.weekday() == 6:
        recommended += timedelta(days=1)

    return FollowUpResponse(
        recommended_days=rule["days"],
        recommended_date=recommended.strftime("%Y-%m-%d"),
        reason=rule["reason"],
    )
