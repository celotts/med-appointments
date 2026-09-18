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
    visual_indicators,
)
from core.base import Base  # noqa: F401, I001, E402
from dependencies import get_current_user  # noqa: E402
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from initial_data import main as init_db  # noqa: E402

from core.config import settings  # noqa: E402

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

# Visual Indicators - manually add routes with proper prefix
from api.endpoints import visual_indicators
from fastapi.routing import APIRoute

for route in visual_indicators.router.routes:
    new_route = APIRoute(
        path="/api/v1/visual-indicators" + route.path,
        endpoint=route.endpoint,
        methods=route.methods,
        name=route.name,
        response_model=route.response_model,
        dependencies=route.dependencies,
        include_in_schema=route.include_in_schema,
        deprecated=route.deprecated,
        response_model_include=route.response_model_include,
        response_model_exclude=route.response_model_exclude,
        response_model_by_alias=route.response_model_by_alias,
        response_model_exclude_unset=route.response_model_exclude_unset,
        response_model_exclude_defaults=route.response_model_exclude_defaults,
        response_model_exclude_none=route.response_model_exclude_none,
        callbacks=route.callbacks,
        openapi_extra=route.openapi_extra,
    )
    app.router.routes.append(new_route)

# Medasist IA
app.include_router(medasist.router)

# Other endpoints
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(integrations.router)
app.include_router(premium.router)


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


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    # Run initialization logic on startup
    # This is safe because the internal logic prevents duplication
    await init_db()
