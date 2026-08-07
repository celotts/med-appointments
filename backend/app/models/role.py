import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from core.db import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Columnas de auditoría
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now())
    deleted_at: Mapped[datetime | None]
    created_by_user_id: Mapped[uuid.UUID | None]
    updated_by_user_id: Mapped[uuid.UUID | None]
    deleted_by_user_id: Mapped[uuid.UUID | None]
    created_by_role_id: Mapped[uuid.UUID | None]
    updated_by_role_id: Mapped[uuid.UUID | None]
    deleted_by_role_id: Mapped[uuid.UUID | None]

    users = relationship("User", back_populates="role")
