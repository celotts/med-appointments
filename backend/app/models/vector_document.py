from __future__ import annotations

from datetime import datetime

from core.db import Base
from sqlalchemy import DateTime, Integer, String, Text, func

# Note: pgvector type can be imported if needed, e.g., from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    def __init__(self, dim=None):
        self.dim = dim

    def get_col_spec(self, **kw):
        if self.dim is not None:
            return f"VECTOR({self.dim})"
        return "VECTOR"


class VectorDocument(Base):
    __tablename__ = "vector_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=True
    )
