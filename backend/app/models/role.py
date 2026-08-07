import uuid
from datetime import datetime

from sqlalchemy import String, func, ForeignKey
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
    updated_at: Mapped[datetime | None] = mapped_column(
        onupdate=func.now(), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id"), nullable=True
    )
    updated_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id"), nullable=True
    )
    deleted_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id"), nullable=True
    )

    users = relationship("User", back_populates="role", foreign_keys="[User.role_id]")
