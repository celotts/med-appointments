from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.visual_indicator import VisualIndicatorConfig
from schemas.visual_indicator import VisualIndicatorConfigCreate, VisualIndicatorConfigUpdate, VisualIndicatorOut

# Mapeo de códigos de estado en español (BD) a códigos de configuración visual
STATUS_TO_VISUAL_CODE = {
    "PENDIENTE": "pending",
    "CONFIRMADA": "confirmed",
    "REAGENDADA": "rescheduled",
    "CANCELADA": "cancelled",
    "ATENDIDA": "attended",
}

# Constantes para estados que ocupan agenda (bloquean horario)
STATUSES_THAT_OCCUPY = {"PENDIENTE", "CONFIRMADA", "REAGENDADA"}

# Estados terminales: no se pueden reprogramar desde aquí
TERMINAL_STATUSES = {"CANCELADA", "ATENDIDA"}

# Tolerancia por defecto para considerar demora (minutos)
DEFAULT_DELAY_TOLERANCE_MINUTES = 15


async def get_visual_config(db: AsyncSession) -> dict[str, VisualIndicatorConfig]:
    """Obtiene toda la configuración visual activa, cacheable."""
    result = await db.execute(
        select(VisualIndicatorConfig).where(VisualIndicatorConfig.is_active == True)
    )
    return {item.code: item for item in result.scalars().all()}


async def get_visual_config_by_code(db: AsyncSession, code: str) -> Optional[VisualIndicatorConfig]:
    result = await db.execute(
        select(VisualIndicatorConfig).where(
            VisualIndicatorConfig.code == code,
            VisualIndicatorConfig.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def create_visual_config(db: AsyncSession, config: VisualIndicatorConfigCreate) -> VisualIndicatorConfig:
    db_config = VisualIndicatorConfig(**config.model_dump())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return db_config


async def update_visual_config(
    db: AsyncSession, db_config: VisualIndicatorConfig, config: VisualIndicatorConfigUpdate
) -> VisualIndicatorConfig:
    update_data = config.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_config, field, value)
    db_config.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_config)
    return db_config


async def delete_visual_config(db: AsyncSession, code: str) -> bool:
    config = await get_visual_config_by_code(db, code)
    if not config:
        return False
    await db.delete(config)
    await db.commit()
    return True


async def get_all_visual_configs(db: AsyncSession) -> list:
    result = await db.execute(select(VisualIndicatorConfig).order_by(VisualIndicatorConfig.sort_order))
    return result.scalars().all()


# Constantes para estados que ocupan agenda (bloquean horario)
STATUSES_THAT_OCCUPY = {"PENDIENTE", "CONFIRMADA", "REAGENDADA"}

# Estados terminales: no se pueden reprogramar desde aquí
TERMINAL_STATUSES = {"CANCELADA", "ATENDIDA"}

# Tolerancia por defecto para considerar demora (minutos)
DEFAULT_DELAY_TOLERANCE_MINUTES = 15


async def get_status_by_code(db: AsyncSession, code: str) -> Optional[object]:
    """Obtiene un estado de cita por su código."""
    from models.appointment_status import AppointmentStatus
    from sqlalchemy import select
    result = await db.execute(
        select(AppointmentStatus).where(AppointmentStatus.code == code)
    )
    return result.scalars().first()


async def get_status_by_id(db: AsyncSession, status_id: int):
    from models.appointment_status import AppointmentStatus
    return await db.get(AppointmentStatus, status_id)


def get_visual_code(status_code: str) -> str:
    """Mapea código de estado en español a código de configuración visual."""
    return {
        "PENDIENTE": "pending",
        "CONFIRMADA": "confirmed",
        "REAGENDADA": "rescheduled",
        "CANCELADA": "cancelled",
        "ATENDIDA": "attended",
    }.get(status_code, status_code.lower())


def compute_visual_indicator(
    appointment,
    config: dict,
    delay_tolerance_minutes: int = DEFAULT_DELAY_TOLERANCE_MINUTES
) -> tuple[str, bool]:
    """
    Calcula el indicador visual para una cita.
    
    Returns:
        tuple: (indicator_code, is_delayed)
    """
    status_code = appointment.status.code if appointment.status else "UNKNOWN"
    now = datetime.now(timezone.utc)
    
    # 1. DEMORADA - máxima prioridad operativa
    if appointment.status and appointment.status.code in ("PENDIENTE", "CONFIRMADA", "REAGENDADA"):
        tolerance = timedelta(minutes=DEFAULT_DELAY_TOLERANCE_MINUTES)
        if datetime.now(timezone.utc) > appointment.start_datetime + tolerance:
            return "delayed", True
    
    # 2. PROXIMIDAD - solo citas futuras en estados que ocupan agenda
    if appointment.start_datetime > datetime.now(timezone.utc):
        if appointment.status and appointment.status.code in STATUSES_THAT_OCCUPY:
            return "proximity_calculated", False  # Se calculará en batch
    
    # 3. Estado normal
    return get_visual_code(appointment.status.code if appointment.status else "UNKNOWN"), False


async def enrich_appointments_with_visuals(
    db,
    appointments: list,
    delay_tolerance_minutes: int = DEFAULT_DELAY_TOLERANCE_MINUTES
) -> list:
    """
    Enriquece una lista de citas con indicadores visuales y las reordena.
    
    Lógica de ordenamiento:
    1. Citas demoradas (delayed) - PRIORIDAD MÁXIMA, al tope
    2. Próximas 3 citas (proximity_rank_1, 2, 3) - ordenadas por proximidad temporal
    3. Resto de citas - ordenadas por fecha/hora
    
    Args:
        db: Sesión de base de datos (opcional, si es None usa configuración por defecto)
        appointments: Lista de objetos Appointment con relationships cargados
        delay_tolerance_minutes: Minutos de tolerancia para considerar demora
    
    Returns:
        Lista enriquecida y reordenada
    """
    if db is not None:
        config = await get_visual_config(db)
    else:
        # Configuración por defecto para tests sin BD
        config = {
            "delayed": type('Config', (), {'code': 'delayed', 'label': 'Demorada', 'hex_color': '#EF4444', 'sort_order': 0}),
            "pending": type('Config', (), {'code': 'pending', 'label': 'Pendiente', 'hex_color': '#6B7280', 'sort_order': 10}),
            "confirmed": type('Config', (), {'code': 'confirmed', 'label': 'Confirmada', 'hex_color': '#3B82F6', 'sort_order': 5}),
            "completed": type('Config', (), {'code': 'completed', 'label': 'Completada', 'hex_color': '#10B981', 'sort_order': 20}),
            "cancelled": type('Config', (), {'code': 'cancelled', 'label': 'Cancelada', 'hex_color': '#EF4444', 'sort_order': 30}),
            "rescheduled": type('Config', (), {'code': 'rescheduled', 'label': 'Reagendada', 'hex_color': '#F59E0B', 'sort_order': 15}),
            "proximity_rank_1": type('Config', (), {'code': 'proximity_rank_1', 'label': 'Próxima 1', 'hex_color': '#10B981', 'sort_order': 1}),
            "proximity_rank_2": type('Config', (), {'code': 'proximity_rank_2', 'label': 'Próxima 2', 'hex_color': '#3B82F6', 'sort_order': 2}),
            "proximity_rank_3": type('Config', (), {'code': 'proximity_rank_3', 'label': 'Próxima 3', 'hex_color': '#F59E0B', 'sort_order': 3}),
        }
    now = datetime.now(timezone.utc)
    tolerance = timedelta(minutes=DEFAULT_DELAY_TOLERANCE_MINUTES)
    
    # Separar citas en categorías
    delayed = []
    upcoming = []
    others = []
    
    for appt in appointments:
        status_code = appt.status.code if appt.status else "UNKNOWN"
        
        # Verificar si está demorada
        if status_code in ("PENDIENTE", "CONFIRMADA", "REAGENDADA"):
            if datetime.now(timezone.utc) > appt.start_datetime + tolerance:
                delayed.append(appt)
                continue
        
        # Verificar si es cita futura en estado que ocupa agenda
        if appt.start_datetime > datetime.now(timezone.utc):
            if status_code in STATUSES_THAT_OCCUPY:
                upcoming.append(appt)
                continue
        
        others.append(appt)
    
    # Proximidad: top 3 futuras más cercanas
    upcoming.sort(key=lambda x: x.start_datetime)
    
    proximity_rank = {}
    for i, appt in enumerate(upcoming[:3]):
        proximity_rank[appt.id] = f"proximity_rank_{i+1}"
    
    # Asignar indicadores visuales
    for appt in appointments:
        if appt.id in proximity_rank:
            code = proximity_rank[appt.id]
            appt.is_delayed = False
        elif appt in delayed:
            code = "delayed"
            appt.is_delayed = True
        else:
            status_code = appt.status.code if appt.status else "UNKNOWN"
            code = {
                "PENDIENTE": "pending",
                "CONFIRMADA": "confirmed",
                "REAGENDADA": "rescheduled",
                "CANCELADA": "cancelled",
                "ATENDIDA": "attended",
            }.get(status_code, status_code.lower())
            appt.is_delayed = False
        
        cfg = config.get(code, config.get("pending"))
        appt.visual_indicator = {
            "code": code,
            "hex_color": cfg.hex_color if cfg else "#6B7280",
            "label": cfg.label if cfg else "Desconocido"
        }
        
        # Calcular minutos hasta la cita
        if appt.start_datetime > datetime.now(timezone.utc):
            appt.minutes_until = int((appt.start_datetime - datetime.now(timezone.utc)).total_seconds() / 60)
        else:
            appt.minutes_until = None
    
    # Reordenar: demoradas primero (por hora), luego por proximidad, luego resto
    def sort_key(a):
        if a.is_delayed:
            return (0, a.start_datetime)
        if hasattr(a, 'id') and a.id in proximity_rank:
            return (1, a.start_datetime)
        return (2, a.start_datetime)
    
    return sorted(appointments, key=sort_key)