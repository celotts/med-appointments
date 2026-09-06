from api.endpoints import (
    citas,
    estados_cita,
    login,
    medicos,
    pacientes,
    rag,
    specialties,
    users,
)
from core.base import Base  # noqa: F401, I001
from fastapi import FastAPI
from initial_data import main as init_db

app = FastAPI(
    title="Medical Appointments RAG API",
    description="API for managing medical appointments with Retrieval-Augmented Generation (RAG) capabilities.",
    version="0.1.0",
)


@app.on_event("startup")
async def on_startup():
    # Run initialization logic on startup
    # This is safe because the internal logic prevents duplication
    await init_db()


@app.get("/")
def read_root():
    return {"status": "ok"}


app.include_router(login.router, prefix="/api/v1", tags=["Login"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(
    specialties.router, prefix="/api/v1/specialties", tags=["Specialties"]
)
app.include_router(medicos.router, prefix="/api/v1/medicos", tags=["Doctors"])
app.include_router(pacientes.router, prefix="/api/v1/pacientes", tags=["Patients"])
app.include_router(
    estados_cita.router, prefix="/api/v1/estados-cita", tags=["Appointment Statuses"]
)
app.include_router(citas.router)
app.include_router(rag.router)
