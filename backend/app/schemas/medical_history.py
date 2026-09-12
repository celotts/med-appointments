from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field
from schemas import BaseSchema as BaseSchema


class MedicalHistoryBase(BaseModel):
    patient_id: str = Field(..., description="ID del paciente (UUID)")
    doctor_id: str = Field(..., description="ID del médico (UUID)")
    diagnosis: str | None = Field(
        default=None, description="Diagnóstico de la consulta"
    )
    prescription: str | None = Field(default=None, description="Receta médica")
    treatment: str | None = Field(default=None, description="Tratamiento indicado")
    ai_summary: str | None = Field(default=None, description="Resumen generado por IA")
    date: dt.date = Field(
        default_factory=dt.date.today, description="Fecha de la consulta"
    )


class MedicalHistoryCreate(MedicalHistoryBase):
    pass


class MedicalHistoryUpdate(BaseModel):
    patient_id: str | None = Field(default=None, description="ID del paciente (UUID)")
    doctor_id: str | None = Field(default=None, description="ID del médico (UUID)")
    diagnosis: str | None = Field(
        default=None, description="Diagnóstico de la consulta"
    )
    prescription: str | None = Field(default=None, description="Receta médica")
    treatment: str | None = Field(default=None, description="Tratamiento indicado")
    ai_summary: str | None = Field(default=None, description="Resumen generado por IA")
    date: dt.date | None = Field(default=None, description="Fecha de la consulta")


class MedicalHistoryResponse(MedicalHistoryBase):
    id: str
    created_at: dt.datetime

    class Config:
        from_attributes = True


# Export for __init__
MedicalHistoryBaseModel = MedicalHistoryBase
MedicalHistoryCreateModel = MedicalHistoryCreate
MedicalHistoryUpdateModel = MedicalHistoryUpdate
MedicalHistoryResponseModel = MedicalHistoryResponse
