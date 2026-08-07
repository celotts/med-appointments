# Este archivo sirve como un punto de entrada para que Alembic y SQLAlchemy
# descubran los modelos de la aplicación.

from core.db import Base  # noqa: F401
from models.role import Role  # noqa: F401, I001
from models.user import User  # noqa: F401
from models.specialty import Specialty  # noqa: F401
