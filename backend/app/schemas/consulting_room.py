from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from schemas import BaseSchema as BaseSchema


class ConsultingRoomBase(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de la consulta"
    )
    address: str | None = Field(
        default=None, max_length=200, description="Dirección de la consulta"
    )
    phone_number: str | None = Field(
        default=None, max_length=15, description="Teléfono de la consulta"
    )


class ConsultingRoomCreate(ConsultingRoomBase):
    pass


class ConsultingRoomUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=100, description="Nombre de la consulta"
    )
    address: str | None = Field(
        default=None, max_length=200, description="Dirección de la consulta"
    )
    phone_number: str | None = Field(
        default=None, max_length=15, description="Teléfono de la consulta"
    )


class ConsultingRoomResponse(ConsultingRoomBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Export for __init__
ConsultingRoomBaseModel = ConsultingRoomBase
ConsultingRoomCreateModel = ConsultingRoomCreate
ConsultingRoomUpdateModel = ConsultingRoomUpdate
ConsultingRoomResponseModel = ConsultingRoomResponse
