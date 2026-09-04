import asyncio

from fastapi import FastAPI

from core.base import Base  # noqa: F401, I001
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
from initial_data import main as init_db

app = FastAPI(
    title="Medical Appointments RAG API",
    description="API para la gestión de citas médicas con capacidades de Búsqueda Aumentada por Generación (RAG).",
    version="0.1.0",
)


@app.on_event("startup")
async def on_startup():
    # Ejecuta la lógica de inicialización en el arranque
    # Esto es seguro porque la lógica interna previene la duplicación
    await init_db()


@app.get("/")
def read_root():
    return {"status": "ok"}


app.include_router(login.router, prefix="/api/v1", tags=["Login"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(
    specialties.router, prefix="/api/v1/specialties", tags=["Especialidades"]
)
app.include_router(medicos.router, prefix="/api/v1/medicos", tags=["Médicos"])
app.include_router(pacientes.router, prefix="/api/v1/pacientes", tags=["Pacientes"])
app.include_router(estados_cita.router, prefix="/api/v1/estados-cita", tags=["Estados de cita"])
app.include_router(citas.router)
app.include_router(rag.router)
