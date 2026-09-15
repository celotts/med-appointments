from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class DoctorBase(BaseModel):
    specialty_id: int
    branch_id: Optional[int] = None
    first_name: str
    last_name: str
    professional_license: str
    email: EmailStr
    phone: Optional[str] = None


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    specialty_id: Optional[int] = None
    branch_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    professional_license: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class DoctorResponse(DoctorBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
