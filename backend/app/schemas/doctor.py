from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class DoctorBase(BaseModel):
    specialty_id: int
    first_name: str
    last_name: str
    professional_license: str
    email: EmailStr
    phone: str | None = None


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    specialty_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    professional_license: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class Doctor(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
