from datetime import datetime
from pydantic import BaseModel, ConfigDict


# Propiedades compartidas por todos los esquemas
class SpecialtyBase(BaseModel):
    nombre: str
    descripcion: str | None = None


# Propiedades para recibir en la creación de una especialidad
class SpecialtyCreate(SpecialtyBase):
    pass


# Propiedades para leer desde la API (incluye el id y la fecha de creación)
class Specialty(SpecialtyBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
