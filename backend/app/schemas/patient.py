from datetime import date, datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class PatientBase(BaseModel):
    first_name: str
    last_name: str
    birth_date: date
    email: EmailStr
    phone: str


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    phone: str | None = None


class Patient(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
