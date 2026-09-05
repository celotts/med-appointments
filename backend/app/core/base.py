# Este archivo sirve como punto de entrada para que Alembic y SQLAlchemy
# descubran todos los modelos de la aplicación.

from core.db import Base  # noqa: F401
from models.audit import AuditLog  # noqa: F401
from models.cita import Cita  # noqa: F401
from models.estado_cita import EstadoCita  # noqa: F401
from models.medico import Medico  # noqa: F401
from models.nota_medica import NotaMedica  # noqa: F401
from models.paciente import Paciente  # noqa: F401
from models.role import Role  # noqa: F401
from models.specialty import Specialty  # noqa: F401
from models.user import User  # noqa: F401
