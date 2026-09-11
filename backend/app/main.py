import sys
from typing import Any

sys.path.insert(0, "/app")
import sys

from api.endpoints import (
    appointment_statuses,
    appointments,
    doctors,
    integrations,
    login,
    medasist,
    notifications,
    patients,
    premium,
    rag,
    reports,
    specialties,
    users,
)

sys.path.insert(0, "/app/app")
from core.base import Base  # noqa: F401, I001
from fastapi import Depends, FastAPI
from initial_data import main as init_db

from app.dependencies import get_current_user

app = FastAPI(
    title="Medical Appointments RAG API",
    description="API for managing medical appointments with Retrieval-Augmented Generation (RAG) capabilities.",
    version="0.2.0",
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
(app.include_router(users.router, prefix="/api/v1", tags=["Users"]),)
app.include_router(
    specialties.router, prefix="/api/v1/specialties", tags=["Specialties"]
)
app.include_router(doctors.router, prefix="/api/v1/doctors", tags=["Doctors"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients"])
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
    return current_user


app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(integrations.router)
app.include_router(premium.router)
