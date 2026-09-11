from __future__ import annotations

from datetime import date, datetime

from core.schemas import BaseSchema as BaseSchema
from pydantic import BaseModel, Field


class MedicalHistoryBase(BaseModel):
    patient_id: str = Field(..., description="ID del paciente (UUID)")
    doctor_id: str = Field(..., description="ID del médico (UUID)")
    diagnosis: str | None = Field(
        default=None, description="Diagnóstico de la consulta"
    )
    prescription: str | None = Field(default=None, description="Receta médica")
    treatment: str | None = Field(default=None, description="Tratamiento indicado")
    ai_summary: str | None = Field(default=None, description="Resumen generado por IA")
    date: date = Field(default_factory=date.today, description="Fecha de la consulta")


class MedicalHistoryCreate(MedicalHistoryBase):
    pass


class MedicalHistoryResponse(MedicalHistoryBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Export for __init__
MedicalHistoryBaseModel = MedicalHistoryBase
MedicalHistoryCreateModel = MedicalHistoryCreate
MedicalHistoryResponseModel = MedicalHistoryResponse
