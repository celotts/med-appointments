from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VisualIndicatorConfigBase(BaseModel):
    code: str
    label: str
    hex_color: str
    sort_order: int = 0
    is_active: bool = True


class VisualIndicatorConfigCreate(VisualIndicatorConfigBase):
    pass


class VisualIndicatorConfigUpdate(BaseModel):
    label: str | None = None
    hex_color: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class VisualIndicatorConfig(VisualIndicatorConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime | None = None


# DTO for appointment visual indicator
class VisualIndicatorOut(BaseModel):
    code: str
    hex_color: str
    label: str
