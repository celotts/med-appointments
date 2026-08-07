import sqlalchemy as sa
from sqlalchemy.orm import relationship

from core.db import Base


class Role(Base):
    __tablename__ = "roles"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, index=True, nullable=False)
    description = sa.Column(sa.String, nullable=True)

    users = relationship("User", back_populates="role")
