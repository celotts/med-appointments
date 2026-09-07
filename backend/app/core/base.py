# This file serves as the entry point for Alembic and SQLAlchemy
# to discover all application models.

from core.db import Base  # noqa: F401
from models.appointment import Appointment  # noqa: F401
from models.appointment_status import AppointmentStatus  # noqa: F401
from models.audit import AuditLog  # noqa: F401
from models.doctor import Doctor  # noqa: F401
from models.medical_note import MedicalNote  # noqa: F401
from models.patient import Patient  # noqa: F401
from models.role import Role  # noqa: F401
from models.specialty import Specialty  # noqa: F401
from models.user import User  # noqa: F401
