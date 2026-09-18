from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from modules.auth.router import router as auth_router
from modules.medasist.router import router as medasist_router
from modules.specialties.router import router as specialties_router
from modules.doctors.router import router as doctors_router
from modules.patients.router import router as patients_router
from modules.branches.router import router as branches_router
from modules.roles.router import router as roles_router
from modules.users.router import router as users_router
from modules.appointments.router import router as appointments_router
from modules.appointment_statuses.router import router as appointment_statuses_router
from modules.medical_notes.router import router as medical_notes_router
from modules.waitlist.router import router as waitlist_router

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, debug=settings.DEBUG)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(medasist_router)
app.include_router(specialties_router)
app.include_router(doctors_router)
app.include_router(patients_router)
app.include_router(branches_router)
app.include_router(roles_router)
app.include_router(users_router)
app.include_router(appointments_router)
app.include_router(appointment_statuses_router)
app.include_router(medical_notes_router)
app.include_router(waitlist_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
