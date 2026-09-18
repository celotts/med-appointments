from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.future import select

from models.appointment import Appointment
from modules.medasist.router import FOLLOW_UP_RULES, _find_free_slots

from ..db import session_factory


async def get_available_slots(doctor_id: int, date: str, duration_minutes: int = 30) -> list[dict[str, str]]:
    """Horarios libres de un doctor en una fecha. date: 'YYYY-MM-DD', duración en minutos."""
    async with session_factory() as db:
        target = datetime.strptime(date, "%Y-%m-%d")
        slots = await _find_free_slots(db, doctor_id, target, duration_minutes)
        return [slot.model_dump() for slot in slots]


async def check_conflict(doctor_id: int, start_datetime: str, end_datetime: str) -> dict[str, Any]:
    """Verifica si un horario propuesto (ISO 8601) se solapa con citas existentes."""
    proposed_start = datetime.fromisoformat(start_datetime)
    proposed_end = datetime.fromisoformat(end_datetime)
    async with session_factory() as db:
        result = await db.execute(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.start_datetime < proposed_end,
                Appointment.end_datetime > proposed_start,
            )
        )
        conflict = result.scalars().first()
        if conflict is None:
            return {"has_conflict": False}
        return {
            "has_conflict": True,
            "conflict_details": (
                f"Overlaps with appointment #{conflict.id} "
                f"({conflict.start_datetime.strftime('%H:%M')} - {conflict.end_datetime.strftime('%H:%M')})"
            ),
            "suggested_fix": "Try shifting 30 minutes later or choosing a different day.",
        }


async def suggest_reschedule(appointment_id: int, preferred_date: str) -> dict[str, Any]:
    """Sugiere alternativas de fecha/hora para reprogramar una cita. preferred_date: 'YYYY-MM-DD'."""
    async with session_factory() as db:
        appt = await db.get(Appointment, appointment_id)
        if appt is None:
            return {"error": "Appointment not found"}

        target_date = datetime.strptime(preferred_date, "%Y-%m-%d")
        duration = int((appt.end_datetime - appt.start_datetime).total_seconds() / 60)
        free_slots = await _find_free_slots(db, appt.doctor_id, target_date, duration)

        if not free_slots:
            return {
                "appointment_id": appt.id,
                "current_start": appt.start_datetime.isoformat(),
                "current_end": appt.end_datetime.isoformat(),
                "suggestions": [],
                "message": "No available slots on the requested date.",
            }

        original_hour = appt.start_datetime.hour
        scored = []
        for slot in free_slots:
            slot_hour = datetime.fromisoformat(slot.start).hour
            time_diff = abs(slot_hour - original_hour)
            score = max(0.0, 1.0 - (time_diff * 0.1))
            if 9 <= slot_hour <= 12:
                score += 0.1
            scored.append({"start": slot.start, "end": slot.end, "score": round(score, 2)})
        scored.sort(key=lambda s: s["score"], reverse=True)

        return {
            "appointment_id": appt.id,
            "current_start": appt.start_datetime.isoformat(),
            "current_end": appt.end_datetime.isoformat(),
            "suggestions": scored[:5],
            "message": f"Found {len(scored)} alternative(s).",
        }


async def suggest_followup(visit_type: str, last_appointment_date: str) -> dict[str, Any]:
    """Sugiere la próxima cita según el tipo de visita: control, urgent, routine o surgery_followup."""
    rule = FOLLOW_UP_RULES.get(visit_type)
    if rule is None:
        return {"error": "Invalid visit type"}
    last_date = datetime.strptime(last_appointment_date, "%Y-%m-%d")
    recommended = last_date + timedelta(days=rule["days"])
    if recommended.weekday() == 5:
        recommended += timedelta(days=2)
    elif recommended.weekday() == 6:
        recommended += timedelta(days=1)
    return {
        "recommended_days": rule["days"],
        "recommended_date": recommended.strftime("%Y-%m-%d"),
        "reason": rule["reason"],
    }


TOOLS: dict[str, object] = {
    "get_available_slots": get_available_slots,
    "check_conflict": check_conflict,
    "suggest_reschedule": suggest_reschedule,
    "suggest_followup": suggest_followup,
}