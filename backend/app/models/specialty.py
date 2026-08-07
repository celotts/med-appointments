import sqlalchemy as sa

from core.db import Base


class Specialty(Base):
    __tablename__ = "specialties"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    nombre = sa.Column(sa.String, index=True, nullable=False)
    descripcion = sa.Column(sa.String, nullable=True)
