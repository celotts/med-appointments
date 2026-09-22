from app.core.db import Base as Base

from .doctor_schedule import DoctorSchedule as DoctorSchedule
from .specialty import Specialty as Specialty
from .doctor import Doctor as Doctor
from .appointment import Appointment as Appointment
from .appointment_status import AppointmentStatus as AppointmentStatus
from .branch import Branch as Branch
from .medical_note import MedicalNote as MedicalNote
from .patient import Patient as Patient
from .role import Role as Role
from .user import User as User
from .vector_document import VectorDocument as VectorDocument
from .consulting_room import ConsultingRoom as ConsultingRoom
from .medical_history import MedicalHistory as MedicalHistory
from .waitlist import Waitlist as Waitlist
from .visual_indicator import VisualIndicatorConfig as VisualIndicatorConfig
