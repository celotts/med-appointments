import sys
from pathlib import Path

# Ensure app directory is in sys.path dynamically regardless of execution directory
app_dir = str(Path(__file__).resolve().parent)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from typing import Any  # noqa: E402

from api.endpoints import (  # noqa: E402
    appointment_statuses,
    appointments,
    consulting_rooms,
    doctor_schedules,
    doctors,
    integrations,
    login,
    medasist,
    medical_histories,
    notifications,
    patients,
    premium,
    rag,
    reports,
    specialties,
    users,
)
from core.base import Base  # noqa: F401, I001, E402
from dependencies import get_current_user  # noqa: E402
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings  # noqa: E402
from initial_data import main as init_db  # noqa: E402

app = FastAPI(
    title="Medical Appointments RAG API",
    description="API for managing medical appointments with Retrieval-Augmented Generation (RAG) capabilities.",
    version="0.2.0",
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    # Run initialization logic on startup
    # This is safe because the internal logic prevents duplication
    await init_db()


@app.get("/")
def read_root():
    return {"status": "ok"}


# Core endpoints
app.include_router(login.router, prefix="/api/v1", tags=["Login"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(
    specialties.router, prefix="/api/v1/specialties", tags=["Specialties"]
)
app.include_router(doctors.router, prefix="/api/v1/doctors", tags=["Doctors"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients"])
app.include_router(
    consulting_rooms.router,
    prefix="/api/v1/consulting-rooms",
    tags=["Consulting Rooms"],
)
app.include_router(
    doctor_schedules.router,
    prefix="/api/v1/doctor-schedules",
    tags=["Doctor Schedules"],
)
app.include_router(
    medical_histories.router,
    prefix="/api/v1/medical-histories",
    tags=["Medical Histories"],
)
app.include_router(
    appointment_statuses.router,
    prefix="/api/v1/appointment-statuses",
    tags=["Appointment Statuses"],
)
app.include_router(appointments.router)
app.include_router(rag.router)

# Medasist IA
app.include_router(medasist.router)

# New endpoints


@app.get(
    "/me",
    response_model=dict,
    summary="Get current authenticated user",
)
async def get_current_user_me(
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Get current authenticated user."""
    return {k: v for k, v in current_user.__dict__.items() if not k.startswith("_")}


app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(integrations.router)
app.include_router(premium.router)
