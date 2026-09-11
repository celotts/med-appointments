# This file serves as the entry point for Alembic and SQLAlchemy
# to discover all application models.

from app.core.db import Base  # noqa: F401
from models.appointment import Appointment  # noqa: F401
from models.appointment_status import AppointmentStatus  # noqa: F401
from models.audit import AuditLog  # noqa: F401
from models.doctor import Doctor  # noqa: F401
from models.medical_note import MedicalNote  # noqa: F401
from models.patient import Patient  # noqa: F401