from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    address: str = "N/A"
    phone: str
    phone2: str
    role_id: uuid.UUID


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    phone2: Optional[str] = None
    role_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
