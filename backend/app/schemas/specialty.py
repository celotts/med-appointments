from pydantic import BaseModel


class SpecialtyBase(BaseModel):
    nombre: str
    descripcion: str | None = None


class SpecialtyCreate(SpecialtyBase):
    pass


class Specialty(SpecialtyBase):
    id: int

    class Config:
        from_attributes = True
