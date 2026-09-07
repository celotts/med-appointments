import uuid
from datetime import datetime

from core.db import Base
from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), default="N/A")
    phone: Mapped[str | None] = mapped_column(String(255), default="0000000000")
    phone2: Mapped[str | None] = mapped_column(String(255), default="0000000000")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roles.id")
    )

    role = relationship("Role", back_populates="users", foreign_keys=[role_id])

    # --- Audit fields (managed by set_audit_role_id trigger in DB) ---
    # These columns are NOT assigned from the application: the database and its
    # triggers son la fuente de verdad. Solo se exponen para lectura.
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True
    )
    updated_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True
    )
    deleted_by_role_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True
    )
