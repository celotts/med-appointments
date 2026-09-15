from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WaitlistBase(BaseModel):
    patient_id: int
    doctor_id: int
    preferred_date: date
    reason: Optional[str] = None
    status: str = "PENDING"


class WaitlistCreate(WaitlistBase):
    pass


class WaitlistUpdate(BaseModel):
    preferred_date: Optional[date] = None
    reason: Optional[str] = None
    status: Optional[str] = None


class WaitlistResponse(WaitlistBase):
    id: int
    created_at: Optional[datetime] = None
    notified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
