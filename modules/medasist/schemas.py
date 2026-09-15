from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class RescheduleRequest(BaseModel):
    appointment_id: int
    preferred_date: str  # YYYY-MM-DD
    preferred_time: Optional[str] = None  # HH:MM


class RescheduleSuggestion(BaseModel):
    start: str
    end: str
    score: float  # 0-1, how good the fit is


class RescheduleResponse(BaseModel):
    appointment_id: int
    current_start: str
    current_end: str
    suggestions: List[RescheduleSuggestion]
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
    exclude_appointment_id: Optional[int] = None


class ConflictCheckResponse(BaseModel):
    has_conflict: bool
    conflict_details: Optional[str] = None
    suggested_fix: Optional[str] = None


class FollowUpRequest(BaseModel):
    patient_id: int
    doctor_id: int
    last_appointment_date: str
    visit_type: str  # control, urgent, routine, surgery_followup


class FollowUpResponse(BaseModel):
    recommended_days: int
    recommended_date: str
    reason: str
