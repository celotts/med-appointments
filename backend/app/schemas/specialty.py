from pydantic import BaseModel


class SpecialtyBase(BaseModel):
    name: str
    description: str | None = None


class SpecialtyCreate(SpecialtyBase):
    pass


class SpecialtyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class Specialty(SpecialtyBase):
    id: int

    class Config:
        from_attributes = True
