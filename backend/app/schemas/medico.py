from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class MedicoBase(BaseModel):
    especialidad_id: int
    nombre: str
    apellido: str
    cedula_profesional: str
    email: EmailStr
    telefono: str | None = None


class MedicoCreate(MedicoBase):
    pass


class MedicoUpdate(BaseModel):
    especialidad_id: int | None = None
    nombre: str | None = None
    apellido: str | None = None
    cedula_profesional: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None


class Medico(MedicoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
