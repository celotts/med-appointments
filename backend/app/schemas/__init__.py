from __future__ import annotations

from pydantic import BaseModel as BaseModel


class BaseSchema(BaseModel):
    """Base schema with common fields for all schemas."""

    pass
