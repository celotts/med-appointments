from fastapi import FastAPI

from app.api.endpoints import specialties

app = FastAPI(
    title="Medical Appointments RAG API",
    description="API para la gestión de citas médicas con capacidades de Búsqueda Aumentada por Generación (RAG).",
    version="0.1.0",
)

app.include_router(
    specialties.router, prefix="/api/v1/specialties", tags=["Specialties"]
)
