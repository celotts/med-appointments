from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SpecialtyBase(BaseModel):
    name: str
    description: Optional[str] = None


class SpecialtyCreate(SpecialtyBase):
    pass


class SpecialtyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class SpecialtyResponse(SpecialtyBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
