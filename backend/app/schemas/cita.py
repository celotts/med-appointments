from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EstadoCitaCodigo(str, Enum):
    """Códigos de estado posibles para una cita médica."""

    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"
    SUSPENDIDA = "SUSPENDIDA"
    REAGENDADA = "REAGENDADA"


# Transiciones válidas: DÓNDE se puede ir desde un estado dado.
TRANSICIONES_VALIDAS: dict[EstadoCitaCodigo, set[EstadoCitaCodigo]] = {
    EstadoCitaCodigo.PENDIENTE: {
        EstadoCitaCodigo.CONFIRMADA,
        EstadoCitaCodigo.COMPLETADA,
        EstadoCitaCodigo.CANCELADA,
        EstadoCitaCodigo.SUSPENDIDA,
        EstadoCitaCodigo.REAGENDADA,
    },
    EstadoCitaCodigo.CONFIRMADA: {
        EstadoCitaCodigo.COMPLETADA,
        EstadoCitaCodigo.CANCELADA,
        EstadoCitaCodigo.SUSPENDIDA,
        EstadoCitaCodigo.REAGENDADA,
    },
    EstadoCitaCodigo.REAGENDADA: {
        EstadoCitaCodigo.CONFIRMADA,
        EstadoCitaCodigo.COMPLETADA,
        EstadoCitaCodigo.CANCELADA,
        EstadoCitaCodigo.SUSPENDIDA,
    },
    EstadoCitaCodigo.SUSPENDIDA: {
        EstadoCitaCodigo.CONFIRMADA,
        EstadoCitaCodigo.COMPLETADA,
        EstadoCitaCodigo.REAGENDADA,
    },
    EstadoCitaCodigo.CANCELADA: set(),
    EstadoCitaCodigo.COMPLETADA: set(),
}


# --- Estados de cita (catálogo) ---
class EstadoCitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    descripcion: str | None = None


# --- Citas ---
class CitaBase(BaseModel):
    paciente_id: int
    medico_id: int
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    motivo_consulta: str


class CitaCreate(CitaBase):
    pass


class CitaUpdate(BaseModel):
    fecha_hora_inicio: datetime | None = None
    fecha_hora_fin: datetime | None = None
    motivo_consulta: str | None = None


class CitaEstadoUpdate(BaseModel):
    """Reagendar o transicionar el estado. `estado` es obligatorio si se usa esta vía."""
    estado: EstadoCitaCodigo


class CitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    medico_id: int
    estado_id: int
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    motivo_consulta: str
    created_at: datetime | None = None
    estado: EstadoCitaOut | None = None


# --- Notas médicas ---
class NotaMedicaBase(BaseModel):
    diagnostico: str
    tratamiento: str | None = None
    observaciones: str | None = None


class NotaMedicaCreate(NotaMedicaBase):
    cita_id: int


class NotaMedicaUpdate(BaseModel):
    diagnostico: str | None = None
    tratamiento: str | None = None
    observaciones: str | None = None


class NotaMedicaOut(NotaMedicaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cita_id: int
    created_at: datetime | None = None
