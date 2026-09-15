from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict


class AppointmentStatusBase(BaseModel):
    code: str
    description: Optional[str] = None


class AppointmentStatusCreate(AppointmentStatusBase):
    pass


class AppointmentStatusUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None


class AppointmentStatusResponse(AppointmentStatusBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
