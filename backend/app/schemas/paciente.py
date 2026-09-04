from datetime import date, datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class PacienteBase(BaseModel):
    nombre: str
    apellido: str
    fecha_nacimiento: date
    email: EmailStr
    telefono: str


class PacienteCreate(PacienteBase):
    pass


class PacienteUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    fecha_nacimiento: date | None = None
    email: EmailStr | None = None
    telefono: str | None = None


class Paciente(PacienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
