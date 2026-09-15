from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class MedicalNoteBase(BaseModel):
    appointment_id: int
    diagnosis: str
    treatment: Optional[str] = None
    observations: Optional[str] = None


class MedicalNoteCreate(MedicalNoteBase):
    pass


class MedicalNoteUpdate(BaseModel):
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    observations: Optional[str] = None


class MedicalNoteResponse(MedicalNoteBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
