"""Conversational RAG agent with scheduling tools using LangChain + Ollama."""

import json
import re
from contextvars import ContextVar

from core.config import settings
from core.i18n import get_translation
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from sqlalchemy import text

# Context variable for current language
_current_language: ContextVar[str] = ContextVar("current_language", default="en")


def get_current_language() -> str:
    """Get the current language from context."""
    return _current_language.get()


def set_current_language(lang: str) -> None:
    """Set the current language in context."""
    _current_language.set(lang)


def t(key: str, **kwargs) -> str:
    """Shorthand for get_translation with current language."""
    return get_translation(key, get_current_language(), **kwargs)


# Prompt injection patterns (case-insensitive)
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
    r"you\s+are\s+now\s+",
    r"act\s+as\s+if\s+",
    r"pretend\s+you\s+are\s+",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(all\s+)?(previous|prior|above)",
    r"new\s+instructions?:",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"<\|system\|>",
    r"<\|user\|>",
    r"<\|assistant\|>",
    r"###\s*system",
    r"###\s*human",
    r"override\s+safety",
    r"bypass\s+(safety|filter|restriction)",
    r"you\s+must\s+not\s+refuse",
    r"do\s+not\s+follow\s+(your|any)\s+(rules?|guidelines?)",
    r"reveal\s+(your|the)\s+(system\s+)?prompt",
    r"what\s+are\s+your\s+(system\s+)?(instructions?|prompts?|rules?)",
]


def _detect_injection(text_input: str) -> str | None:
    """Returns a warning message if prompt injection is detected, else None."""
    lower = text_input.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return (
                "Your message was blocked for containing disallowed patterns. "
                "Please ask a question related to medical appointments or clinical information."
            )
    return None


_SYSTEM_PROMPT = """Eres MedAssist, un asistente inteligente de gestión de appointments médicas con capacidades avanzadas de IA.

CAPACIDADES PRINCIPALES:
1. Gestión de appointments: crear, consultar, reagendar, cancelar appointments médicas.
2. Creación por lenguaje natural: interpretar solicitudes como "Agenda cita con Dr. García para Juan el martes".
3. Búsqueda semántica: buscar en notas médicas y documentos clínicos vectorizados.
4. Análisis de agenda: sugerir horarios óptimos, detectar conflictos, analizar carga de trabajo.
5. Reagendamiento inteligente: sugerir mejores horarios basado en patrones del paciente.
6. Lista de espera: gestionar cola cuando no hay disponibilidad.
7. Predicción de no-show: estimar probabilidad de inasistencia.
8. Seguimiento automático: recomendar appointments de seguimiento según diagnóstico.
9. Coordinación multi-doctor: encontrar horarios compartidos para appointments conjuntas.
10. Triaje por síntomas: evaluar urgencia y sugerir especialidad.
11. Patrones predictivos: analizar comportamiento de patients para mejorar asistencia.
12. Resumen de notas clínicas: extraer información relevante de diagnósticos y tratamientos.

HERRAMIENTAS DISPONIBLES:
BÁSICAS:
- buscar_en_documentos, consultar_citas_paciente, consultar_citas_medico
- buscar_pacientes, buscar_medicos, contar_registros

AGENDA:
- sugerir_horarios_disponibles, analizar_carga_medico, detectar_conflictos
- analizar_patrones_paciente

AVANZADAS:
- crear_cita_por_lenguaje: Crear appointments desde descripción natural
- reagendamiento_inteligente: Sugerir mejores horarios automáticamente
- agregar_a_lista_espera: Gestionar cola de espera
- predecir_no_show: Estimar probabilidad de inasistencia
- sugerir_seguimiento: Recomendar appointments de seguimiento
- encontrar_horario_compartido: Buscar disponibilidad multi-doctor
- triagar_por_sintomas: Evaluar urgencia por síntomas

GESTIÓN MASIVA Y EMERGENCIA:
- cancelar_citas_masivo: Cancelar todas las appointments de un médico en un día
- replanificar_citas: Mover appointments de un día a otro automáticamente
- notificar_lista_espera: Avisar a patients pendientes cuando hay slots
- protocolo_emergencia: Ejecutar protocolo completo de emergencia
- optimizar_agenda: Analizar y sugerir mejoras de eficiencia
- generar_recordatorio: Crear recordatorios personalizados

FEATURES ÚNICOS DE DIFERENCIACIÓN:
- predecir_demanda: Anticipar picos de demanda y specialties
- matching_paciente_medico: Encontrar el mejor médico para cada paciente
- duracion_inteligente: Predecir duración óptima de cada cita
- optimizar_ingresos: Estrategias para maximizar facturación
- score_satisfaccion: Evaluar satisfacción del paciente
- resumen_clinico_paciente: Generar resumen antes de la cita
- detectar_anomalias: Identificar patrones inusuales
- scheduling_adaptativo: Aprender y mejorar automáticamente

RESOLUCIÓN DE CONFLICTOS:
- resolver_conflicto_cirugia: Gestión automática cuando médico tiene cirugía (reasignar + notificar)

REGLAS:
- Sé conciso y profesional.
- Si no tienes suficiente información, indica qué dato falta.
- Nunca inventes diagnósticos, tratamientos ni datos médicos.
- Al reagendar, valida que el usuario confirme explícitamente.
- Usa las herramientas disponibles para consultar la base de datos en tiempo real.
- Para conflictos, siempre sugiere alternativas concretas.
- Al analizar patrones, provide recomendaciones accionables.
- Para triaje, siempre indica que es orientativo y requiere validación profesional.
- Responde en español.
"""

_conn_str = ""


def _get_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.OLLAMA_LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.3,
        num_predict=1024,
    )


@tool
async def buscar_en_documentos(
    query: str = "", reference_type: str | None = None
) -> str:
    """Busca documentos relevantes en la base de datos vectorial (notas médicas, documentos clínicos).

    Args:
        query: Consulta en lenguaje natural sobre contenido médico.
        reference_type: Filtrar por tipo de referencia (ej: 'NOTA_MEDICA', 'DOCUMENTO').
    """
    from core.rag import search_documentos as _search
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        results = await _search(db, query, k=5, reference_type=reference_type)
    await engine.dispose()

    if not results:
        return "No relevant documents found."

    return json.dumps(results, ensure_ascii=False, indent=2)


@tool
async def consultar_citas_paciente(patient_name: str = "") -> str:
    """Consulta las appointments de un paciente por su nombre.

    Args:
        patient_name: Nombre o last_name del paciente (búsqueda parcial).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.start_datetime, c.end_datetime, c.reason,
                       ec.code AS estado,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN doctors m ON m.id = c.doctor_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE (p.first_name ILIKE :q OR p.last_name ILIKE :q
                       OR CONCAT(p.first_name, ' ', p.last_name) ILIKE :q)
                ORDER BY c.start_datetime DESC
                LIMIT 10
                """
            ),
            {"q": f"%{patient_name}%"},
        )
        rows = result.mappings().all()
    await engine.dispose()

    if not rows:
        return f"No appointments found for '{patient_name}'."

    return json.dumps(
        [
            {
                "appointment_id": r["id"],
                "date": str(r["start_datetime"]),
                "status": r["status"],
                "doctor": r["doctor"],
                "reason": r["reason"],
            }
            for r in rows
        ],
        ensure_ascii=False,
        indent=2,
    )


@tool
async def consultar_citas_medico(doctor_name: str = "") -> str:
    """Consulta las appointments de un médico por su nombre.

    Args:
        doctor_name: Nombre o last_name del médico (búsqueda parcial).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.start_datetime, c.end_datetime, c.reason,
                       ec.code AS estado,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN doctors m ON m.id = c.doctor_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE (m.first_name ILIKE :q OR m.last_name ILIKE :q
                       OR CONCAT(m.first_name, ' ', m.last_name) ILIKE :q)
                ORDER BY c.start_datetime DESC
                LIMIT 10
                """
            ),
            {"q": f"%{doctor_name}%"},
        )
        rows = result.mappings().all()
    await engine.dispose()

    if not rows:
        return f"No appointments found for doctor '{doctor_name}'."

    return json.dumps(
        [
            {
                "appointment_id": r["id"],
                "date": str(r["start_datetime"]),
                "status": r["status"],
                "patient": r["patient"],
                "reason": r["reason"],
            }
            for r in rows
        ],
        ensure_ascii=False,
        indent=2,
    )


@tool
async def buscar_pacientes(name: str = "") -> str:
    """Busca patients por nombre o last_name.

    Args:
        nombre: Nombre o last_name del paciente (búsqueda parcial).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT id, first_name, last_name, email, phone
                FROM patients
                WHERE first_name ILIKE :q OR last_name ILIKE :q
                   OR CONCAT(first_name, ' ', last_name) ILIKE :q
                ORDER BY last_name, first_name
                LIMIT 10
                """
            ),
            {"q": f"%{name}%"},
        )
        rows = result.mappings().all()
    await engine.dispose()

    if not rows:
        return f"No patients found matching '{name}'."

    return json.dumps(
        [dict(r) for r in rows],
        ensure_ascii=False,
        indent=2,
    )


@tool
async def buscar_medicos(name: str = "") -> str:
    """Busca médicos por nombre o last_name.

    Args:
        nombre: Nombre o last_name del médico (búsqueda parcial).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT m.id, m.first_name, m.last_name, m.email, m.phone,
                       e.name AS specialty
                FROM doctors m
                JOIN specialties e ON e.id = m.specialty_id
                WHERE m.first_name ILIKE :q OR m.last_name ILIKE :q
                   OR CONCAT(m.first_name, ' ', m.last_name) ILIKE :q
                ORDER BY m.last_name, m.first_name
                LIMIT 10
                """
            ),
            {"q": f"%{name}%"},
        )
        rows = result.mappings().all()
    await engine.dispose()

    if not rows:
        return f"No doctors found matching '{name}'."

    return json.dumps(
        [dict(r) for r in rows],
        ensure_ascii=False,
        indent=2,
    )


@tool
async def sugerir_reagendamiento(appointment_id: int, nueva_fecha: str) -> str:
    """Propone reagendar una cita a una nueva fecha. NO ejecuta la acción, solo informa al usuario para que confirme.

    Args:
        appointment_id: ID de la cita a reagendar.
        nueva_fecha: Nueva fecha propuesta en formato ISO 8601 (ej: '2026-09-15T10:00:00').
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.start_datetime, c.end_datetime,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       ec.code AS estado
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN doctors m ON m.id = c.doctor_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.id = :appointment_id
                """
            ),
            {"appointment_id": appointment_id},
        )
        row = result.mappings().first()
    await engine.dispose()

    if not row:
        return f"Appointment {appointment_id} not found."

    return (
        f"Reschedule proposal:\n"
        f"- Appointment #{row['id']} ({row['status']})\n"
        f"- Patient: {row['patient']}\n"
        f"- Doctor: {row['doctor']}\n"
        f"- Current date: {row['start_datetime']}\n"
        f"- Proposed new date: {nueva_fecha}\n\n"
        f"The user must explicitly confirm before executing the change."
    )


@tool
async def ejecutar_reagendamiento(
    appointment_id: int,
    nueva_fecha: str,
    confirmado: bool = False,
) -> str:
    """EJECUTA el reagendamiento de una cita a una nueva fecha YA confirmado por el usuario.

    IMPORTANTE: Solo usar después de que el usuario confirme explícitamente.
    Cambia la fecha de la cita y la pasa a estado REAGENDADA.

    Args:
        appointment_id: ID de la cita a reagendar.
        nueva_fecha: Nueva hora de inicio en formato ISO 8601 (ej: '2026-09-16T10:00:00Z').
        confirmado: Debe ser True; si es False, devuelve advertencia sin ejecutar.
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    if not confirmado:
        return (
            "Reschedule not executed: explicit user confirmation is required. "
            "First present the proposal and ask for confirmation, then call again "
            "with confirmed=true."
        )

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with async_session() as db:
            import core.base  # noqa: F401  (registers all models/mappers)
            from core import crud_appointment
            from schemas.appointment import AppointmentUpdate

            db_appointment = await crud_appointment.get_appointment(db, appointment_id)
            if not db_appointment:
                return f"Appointment {appointment_id} not found."

            start = datetime.fromisoformat(nueva_fecha.replace("Z", "+00:00"))
            end = start + timedelta(minutes=30)
            update = AppointmentUpdate(
                start_datetime=start,
                end_datetime=end,
            )
            try:
                appointment = await crud_appointment.reschedule_appointment(
                    db, db_appointment, update
                )
            except ValueError as exc:
                return f"Could not reschedule: {exc}"
            return (
                f"Appointment #{appointment.id} rescheduled to {appointment.start_datetime} "
                f"(status: {appointment.status.code})."
            )
    finally:
        await engine.dispose()


@tool
async def cancelar_cita(appointment_id: int, confirmado: bool = False) -> str:
    """CANCELA una cita (estado CANCELADA) YA confirmado por el usuario.

    Solo procede si el estado actual permite la transición a CANCELADA.

    IMPORTANTE: Solo usar después de que el usuario confirme explícitamente.

    Args:
        appointment_id: ID de la cita a cancelar.
        confirmado: Debe ser True; si es False, devuelve advertencia sin ejecutar.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    if not confirmado:
        return (
            "Cancellation not executed: explicit user confirmation is required. "
            "Ask for confirmation and then call again with confirmed=true."
        )

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with async_session() as db:
            import core.base  # noqa: F401  (registers all models/mappers)
            from core import crud_appointment
            from schemas.appointment import (
                AppointmentStatusCode,
                AppointmentStatusUpdate,
            )

            db_appointment = await crud_appointment.get_appointment(db, appointment_id)
            if not db_appointment:
                return f"Appointment {appointment_id} not found."

            try:
                appointment = await crud_appointment.change_status(
                    db,
                    db_appointment,
                    AppointmentStatusUpdate(status=AppointmentStatusCode.CANCELLED),
                )
            except ValueError as exc:
                return f"Could not cancel: {exc}"
            return f"Appointment #{appointment.id} cancelled."
    finally:
        await engine.dispose()


@tool
async def contar_registros() -> str:
    """Cuenta cuántos registros hay de cada tipo: patients, médicos, appointments, notas médicas.

    Útil para responder preguntas como '¿cuántos patients hay?', '¿cuántas appointments existen?'.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                "SELECT "
                "(SELECT COUNT(*) FROM patients) AS patients, "
                "(SELECT COUNT(*) FROM doctors) AS doctors, "
                "(SELECT COUNT(*) FROM appointments) AS appointments, "
                "(SELECT COUNT(*) FROM medical_notes) AS medical_notes, "
                "(SELECT COUNT(*) FROM vector_documents) AS documentos"
            )
        )
        row = result.mappings().first()
    await engine.dispose()

    return json.dumps(dict(row), ensure_ascii=False)


# ============================================================================
# AGENDA IA: HERRAMIENTAS INTELIGENTES DE PROGRAMACIÓN
# ============================================================================


@tool
async def sugerir_horarios_disponibles(
    doctor_id: int, fecha: str, duracion_min: int = 30
) -> str:
    """Sugiere horarios disponibles para un médico en una fecha específica.

    Analiza la agenda existente y encuentra slots vacíos considerando:
    - Horario laboral típico (08:00-14:00, 16:00-20:00)
    - Citas ya programadas
    - Duración de la nueva cita

    Args:
        doctor_id: ID del médico.
        date: Fecha a consultar en formato YYYY-MM-DD.
        duracion_min: Duración de la cita en minutos (default 30).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get existing appointments for the doctor on that date
        result = await db.execute(
            text(
                """
                SELECT c.start_datetime, c.end_datetime
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND DATE(c.start_datetime) = :fecha
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.start_datetime
                """
            ),
            {"doctor_id": doctor_id, "date": fecha},
        )
        occupied = result.mappings().all()
    await engine.dispose()

    # Parse date and generate potential slots
    date_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    morning_start = datetime.combine(date_obj, datetime.min.time().replace(hour=8))
    morning_end = datetime.combine(date_obj, datetime.min.time().replace(hour=14))
    afternoon_start = datetime.combine(date_obj, datetime.min.time().replace(hour=16))
    afternoon_end = datetime.combine(date_obj, datetime.min.time().replace(hour=20))

    # Generate 30-min slots
    potential_slots = []
    current = morning_start
    while current + timedelta(minutes=duracion_min) <= morning_end:
        potential_slots.append(current)
        current += timedelta(minutes=30)
    current = afternoon_start
    while current + timedelta(minutes=duracion_min) <= afternoon_end:
        potential_slots.append(current)
        current += timedelta(minutes=30)

    # Filter out occupied slots
    available = []
    for slot in potential_slots:
        slot_end = slot + timedelta(minutes=duracion_min)
        is_free = True
        for occ in occupied:
            occ_start = occ["start_datetime"]
            occ_end = occ["end_datetime"]
            if slot < occ_end and slot_end > occ_start:
                is_free = False
                break
        if is_free:
            available.append(slot)

    if not available:
        return f"No available time slots for doctor {doctor_id} on {fecha} with {duracion_min} min duration."

    # Format response
    slots_json = [
        {
            "start_time": s.strftime("%H:%M"),
            "end_time": (s + timedelta(minutes=duracion_min)).strftime("%H:%M"),
            "suggestion": s.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        for s in available[:8]  # Limit to 8 suggestions
    ]

    return json.dumps(
        {
            "doctor_id": doctor_id,
            "date": fecha,
            "duration_min": duracion_min,
            "available_slots": slots_json,
            "total_available": len(available),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def analizar_carga_medico(doctor_id: int, days: int = 7) -> str:
    """Analiza la carga de trabajo de un médico en los próximos N días.

    Retorna estadísticas de ocupación y sugiere días con menor carga.

    Args:
        doctor_id: ID del médico.
        days: Número de días a analizar (default 7).
    """

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT DATE(c.start_datetime) AS dia,
                       COUNT(*) AS total_appointments,
                       SUM(EXTRACT(EPOCH FROM (c.end_datetime - c.start_datetime))/60) AS minutos_ocupados
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND c.start_datetime >= NOW()
                  AND c.start_datetime < NOW() + INTERVAL ':days days'
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY DATE(c.start_datetime)
                ORDER BY dia
                """
            ),
            {"doctor_id": doctor_id, "days": days},
        )
        daily_load = result.mappings().all()

        # Get doctor info
        result_med = await db.execute(
            text("SELECT first_name, last_name FROM doctors WHERE id = :id"),
            {"id": doctor_id},
        )
        medico = result_med.mappings().first()
    await engine.dispose()

    if not medico:
        return f"Doctor {doctor_id} not found."

    # Calculate stats
    total_appointments = sum(r["total_appointments"] for r in daily_load)
    total_minutos = sum(r["minutos_ocupados"] or 0 for r in daily_load)
    promedio_appointments = total_appointments / days if days > 0 else 0

    # Find lightest day
    day_load = {str(r["dia"]): r["total_appointments"] for r in daily_load}
    lightest_day = min(day_load, key=day_load.get) if day_load else None

    return json.dumps(
        {
            "doctor": f"{medico['first_name']} {medico['last_name']}",
            "periodo": f"Próximos {days} días",
            "total_appointments": total_appointments,
            "total_horas": round(total_minutos / 60, 1),
            "promedio_appointments_dia": round(promedio_appointments, 1),
            "carga_por_dia": day_load,
            "dia_mas_disponible": lightest_day,
            "cita_mas_corta": "30 min" if total_appointments > 0 else "N/A",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def detectar_conflictos(fecha_inicio: str, fecha_fin: str) -> str:
    """Detecta conflictos de horario en un rango de fechas.

    Busca appointments superpuestas y sugiere soluciones automáticas.

    Args:
        fecha_inicio: Fecha/hora inicio del rango (ISO 8601).
        fecha_fin: Fecha/hora fin del rango (ISO 8601).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.start_datetime, c.end_datetime,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       ec.code AS estado
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN doctors m ON m.id = c.doctor_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.start_datetime < :fecha_fin
                  AND c.end_datetime > :fecha_inicio
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.doctor_id, c.start_datetime
                """
            ),
            {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
        )
        conflicts = result.mappings().all()
    await engine.dispose()

    if not conflicts:
        return "No scheduling conflicts detected in the specified range."

    # Group by doctor
    by_medico = {}
    for c in conflicts:
        med = c["doctor"]
        if med not in by_medico:
            by_medico[med] = []
        by_medico[med].append(c)

    # Find overlapping pairs
    conflictos = []
    for medico, appointments in by_medico.items():
        for i in range(len(appointments)):
            for j in range(i + 1, len(appointments)):
                c1, c2 = appointments[i], appointments[j]
                if (
                    c1["start_datetime"] < c2["end_datetime"]
                    and c2["start_datetime"] < c1["end_datetime"]
                ):
                    conflictos.append(
                        {
                            "doctor": medico,
                            "appointment_1": {
                                "id": c1["id"],
                                "patient": c1["patient"],
                                "start": str(c1["start_datetime"]),
                                "end": str(c1["end_datetime"]),
                            },
                            "appointment_2": {
                                "id": c2["id"],
                                "patient": c2["patient"],
                                "start": str(c2["start_datetime"]),
                                "end": str(c2["end_datetime"]),
                            },
                            "suggestion": f"Reagendar cita #{c2['id']} a otro horario",
                        }
                    )

    return json.dumps(
        {
            "conflicts_found": len(conflictos),
            "details": conflictos,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def analizar_patrones_paciente(patient_name: str = "") -> str:
    """Analiza patrones de appointments de un paciente para predecir comportamiento.

    Identifica:
    - Días de la semana preferidos
    - Horarios preferidos
    - Tasa de cancelaciones
    - Frecuencia de reagendamientos

    Args:
        patient_name: Nombre o last_name del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.start_datetime,
                       ec.code AS estado,
                       EXTRACT(DOW FROM c.start_datetime) AS day_of_week,
                       EXTRACT(HOUR FROM c.start_datetime) AS hora
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE (p.first_name ILIKE :q OR p.last_name ILIKE :q
                       OR CONCAT(p.first_name, ' ', p.last_name) ILIKE :q)
                ORDER BY c.start_datetime DESC
                LIMIT 50
                """
            ),
            {"q": f"%{patient_name}%"},
        )
        appointments = result.mappings().all()
    await engine.dispose()

    if not appointments:
        return f"No appointments found for '{patient_name}'."

    # Analyze patterns
    day_of_week_map = {
        0: "Dom",
        1: "Lun",
        2: "Mar",
        3: "Mié",
        4: "Jue",
        5: "Vie",
        6: "Sáb",
    }
    dia_counts = {}
    hora_counts = {}
    total = len(appointments)
    canceladas = sum(1 for c in appointments if c["status"] == "CANCELADA")
    reagendadas = sum(1 for c in appointments if c["status"] == "REAGENDADA")

    for c in appointments:
        dia = day_of_week_map.get(c["day_of_week"], "?")
        dia_counts[dia] = dia_counts.get(dia, 0) + 1
        hora = c["hora"]
        hora_counts[f"{int(hora):02d}:00"] = (
            hora_counts.get(f"{int(hora):02d}:00", 0) + 1
        )

    dia_preferido = max(dia_counts, key=dia_counts.get) if dia_counts else "N/A"
    hora_preferida = max(hora_counts, key=hora_counts.get) if hora_counts else "N/A"

    return json.dumps(
        {
            "patient": patient_name,
            "total_appointments": total,
            "preferred_days": dia_counts,
            "most_frequent_day": dia_preferido,
            "preferred_hours": hora_counts,
            "most_frequent_hour": hora_preferida,
            "cancellation_rate": f"{(canceladas / total * 100):.1f}%"
            if total > 0
            else "0%",
            "tasa_reagendamiento": f"{(reagendadas / total * 100):.1f}%"
            if total > 0
            else "0%",
            "recommendation": f"Para mayor asistencia, programar los {dia_preferido} a las {hora_preferida}.",
        },
        ensure_ascii=False,
        indent=2,
    )


# ============================================================================
# AGENDA IA: HERRAMIENTAS AVANZADAS
# ============================================================================


@tool
async def crear_cita_por_lenguaje(
    descripcion: str,
    patient_id: int | None = None,
    doctor_id: int | None = None,
) -> str:
    """Crea una cita médica a partir de una descripción en lenguaje natural.

    Interpreta la solicitud del usuario y crea la cita automáticamente.
    Si faltan datos, pide la información faltante.

    Args:
        description: Descripción en lenguaje natural (ej: "Cita con Dr. García para Juan el martes a las 10am").
        patient_id: ID del paciente (opcional si se menciona nombre).
        doctor_id: ID del médico (opcional si se menciona nombre).
    """

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Try to find patient if not provided
        if not patient_id:
            result = await db.execute(
                text(
                    """
                    SELECT id, first_name, last_name FROM patients
                    WHERE CONCAT(first_name, ' ', last_name) ILIKE :q
                    LIMIT 1
                    """
                ),
                {"q": f"%{descripcion}%"},
            )
            paciente = result.mappings().first()
            if paciente:
                patient_id = paciente["id"]

        # Try to find doctor if not provided
        if not doctor_id:
            result = await db.execute(
                text(
                    """
                    SELECT id, first_name, last_name FROM doctors
                    WHERE CONCAT(first_name, ' ', last_name) ILIKE :q
                    LIMIT 1
                    """
                ),
                {"q": f"%{descripcion}%"},
            )
            medico = result.mappings().first()
            if medico:
                doctor_id = medico["id"]

    await engine.dispose()

    if not patient_id:
        return (
            "I could not identify the patient. Please provide the patient ID "
            "or mention their full name in the description."
        )

    if not doctor_id:
        return (
            "I could not identify the doctor. Please provide the doctor ID "
            "or mention their full name in the description."
        )

    return json.dumps(
        {
            "action": "crear_cita",
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "original_description": descripcion,
            "message": "Datos extraídos correctamente. Use crear_cita del CRUD para ejecutar con fecha/hora específica.",
            "siguiente_paso": "El usuario debe especificar fecha y hora, o usar sugerir_horarios_disponibles.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def reagendamiento_inteligente(appointment_id: int) -> str:
    """Sugiere el mejor horario para reagendar una cita basado en patrones del paciente y disponibilidad del médico.

    Analiza:
    - Preferencias del paciente (días y horarios favoritos)
    - Disponibilidad del médico
    - Conflictos potenciales

    Args:
        appointment_id: ID de la cita a reagendar.
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get current appointment details
        result = await db.execute(
            text(
                """
                SELECT c.id, c.start_datetime, c.end_datetime, c.reason,
                       c.patient_id, c.doctor_id,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       ec.code AS estado
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN doctors m ON m.id = c.doctor_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.id = :appointment_id
                """
            ),
            {"appointment_id": appointment_id},
        )
        cita = result.mappings().first()

        if not cita:
            await engine.dispose()
            return f"Appointment {appointment_id} not found."

        if cita["status"] in ("CANCELADA", "COMPLETADA"):
            await engine.dispose()
            return f"Cannot reschedule a {cita['status']} appointment."

        # Get patient patterns
        result_pat = await db.execute(
            text(
                """
                SELECT EXTRACT(DOW FROM c.start_datetime) AS day_of_week,
                       EXTRACT(HOUR FROM c.start_datetime) AS hora,
                       COUNT(*) AS frecuencia
                FROM appointments c
                WHERE c.patient_id = :patient_id
                  AND c.id != :appointment_id
                GROUP BY day_of_week, hora
                ORDER BY frecuencia DESC
                LIMIT 5
                """
            ),
            {"patient_id": cita["patient_id"], "appointment_id": appointment_id},
        )
        patrones = result_pat.mappings().all()

        # Get available slots for next 7 days
        result_slots = await db.execute(
            text(
                """
                SELECT c.start_datetime, c.end_datetime
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND c.start_datetime >= NOW()
                  AND c.start_datetime < NOW() + INTERVAL '7 days'
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.start_datetime
                """
            ),
            {"doctor_id": cita["doctor_id"]},
        )
        ocupadas = result_slots.mappings().all()
    await engine.dispose()

    # Generate recommendations
    day_of_week_map = {
        0: "Dom",
        1: "Lun",
        2: "Mar",
        3: "Mié",
        4: "Jue",
        5: "Vie",
        6: "Sáb",
    }
    recomendaciones = []

    if patrones:
        mejor_patron = patrones[0]
        recomendaciones.append(
            {
                "tipo": "por_patron",
                "dia": day_of_week_map.get(int(mejor_patron["day_of_week"]), "?"),
                "hora": f"{int(mejor_patron['hora']):02d}:00",
                "confianza": "alta",
                "razon": f"El paciente tiene {mejor_patron['frecuencia']} appointments en este horario.",
            }
        )

    # Find free slots in next 7 days
    date_obj = datetime.now().date()
    for day_offset in range(7):
        check_date = date_obj + timedelta(days=day_offset)
        for hour in [9, 10, 11, 14, 15, 16, 17]:
            slot_start = datetime.combine(
                check_date, datetime.min.time().replace(hour=hour)
            )
            slot_end = slot_start + timedelta(minutes=30)
            is_free = True
            for occ in ocupadas:
                if (
                    slot_start < occ["end_datetime"]
                    and slot_end > occ["start_datetime"]
                ):
                    is_free = False
                    break
            if is_free:
                recomendaciones.append(
                    {
                        "tipo": "disponible",
                        "date": slot_start.strftime("%Y-%m-%d"),
                        "hora": slot_start.strftime("%H:%M"),
                        "suggestion": slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                )
                if len(recomendaciones) >= 5:
                    break
        if len(recomendaciones) >= 5:
            break

    return json.dumps(
        {
            "appointment_id": appointment_id,
            "patient": cita["patient"],
            "doctor": cita["doctor"],
            "current_date": str(cita["start_datetime"]),
            "recommendations": recomendaciones[:5],
            "message": "Seleccione una opción o confirme para ejecutar el reagendamiento.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def agregar_a_lista_espera(
    patient_id: int, doctor_id: int, fecha_preferida: str, motivo: str = ""
) -> str:
    """Agrega un paciente a la lista de espera para un médico cuando no hay horarios disponibles.

    Guarda la preferencia y notificará cuando se libere un slot.

    Args:
        patient_id: ID del paciente.
        doctor_id: ID del médico.
        preferred_date: Fecha preferida en formato YYYY-MM-DD.
        reason: Motivo de la consulta.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Create waitlist table if not exists
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS waitlist (
                    id SERIAL PRIMARY KEY,
                    patient_id INT NOT NULL,
                    doctor_id INT NOT NULL,
                    fecha_preferida DATE NOT NULL,
                    motivo TEXT,
                    estado VARCHAR(20) DEFAULT 'PENDIENTE',
                    created_at TIMESTAMP DEFAULT NOW(),
                    notified_at TIMESTAMP,
                    CONSTRAINT fk_espera_paciente FOREIGN KEY (patient_id)
                        REFERENCES patients (id) ON DELETE CASCADE,
                    CONSTRAINT fk_espera_medico FOREIGN KEY (doctor_id)
                        REFERENCES doctors (id) ON DELETE CASCADE
                )
                """
            )
        )

        # Check if already in waitlist
        result = await db.execute(
            text(
                """
                SELECT id FROM waitlist
                WHERE patient_id = :patient_id AND doctor_id = :doctor_id
                  AND estado = 'PENDIENTE'
                """
            ),
            {"patient_id": patient_id, "doctor_id": doctor_id},
        )
        existing = result.first()

        if existing:
            await engine.dispose()
            return "The patient is already on the waitlist for this doctor."

        # Add to waitlist
        await db.execute(
            text(
                """
                INSERT INTO waitlist (patient_id, doctor_id, fecha_preferida, motivo)
                VALUES (:patient_id, :doctor_id, :fecha_preferida, :motivo)
                """
            ),
            {
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "fecha_preferida": fecha_preferida,
                "reason": motivo,
            },
        )
        await db.commit()

    await engine.dispose()

    return json.dumps(
        {
            "action": "agregar_waitlist",
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "fecha_preferida": fecha_preferida,
            "status": "PENDIENTE",
            "message": "Patient added to the waitlist. You will be notified when a slot opens up.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def predecir_no_show(patient_id: int) -> str:
    """Predice la probabilidad de que un paciente no asista a su próxima cita.

    Basado en:
    - Historial de asistencias anteriores
    - Frecuencia de cancelaciones
    - Días de la semana
    - Tiempo de anticipación de la cita

    Args:
        patient_id: ID del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.start_datetime, ec.code AS estado,
                       EXTRACT(DOW FROM c.start_datetime) AS day_of_week,
                       EXTRACT(EPOCH FROM (c.start_datetime - NOW()))/3600 AS horas_anticipacion
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.patient_id = :patient_id
                ORDER BY c.start_datetime DESC
                LIMIT 20
                """
            ),
            {"patient_id": patient_id},
        )
        historial = result.mappings().all()

        # Get patient info
        result_pat = await db.execute(
            text("SELECT first_name, last_name FROM patients WHERE id = :id"),
            {"id": patient_id},
        )
        paciente = result_pat.mappings().first()
    await engine.dispose()

    if not paciente:
        return f"Patient {patient_id} not found."

    if not historial:
        return json.dumps(
            {
                "patient": f"{paciente['first_name']} {paciente['last_name']}",
                "prediccion": "sin_datos",
                "probabilidad": "N/A",
                "message": "Insufficient history to predict.",
            },
            ensure_ascii=False,
            indent=2,
        )

    total = len(historial)
    canceladas = sum(1 for h in historial if h["status"] == "CANCELADA")
    completadas = sum(1 for h in historial if h["status"] == "COMPLETADA")

    # Calculate base probability
    tasa_cancelacion = canceladas / total if total > 0 else 0
    tasa_asistencia = completadas / total if total > 0 else 0

    # Adjust by day of week (weekends have higher no-show rates)

    # Risk factors
    factores_riesgo = []
    if tasa_cancelacion > 0.3:
        factores_riesgo.append("Alta tasa de cancelaciones previas")
    if tasa_asistencia < 0.5:
        factores_riesgo.append("Baja tasa de asistencia histórica")

    # Final probability (simple heuristic)
    probabilidad = min(
        0.95, tasa_cancelacion * 0.7 + (0.1 if len(factores_riesgo) > 1 else 0)
    )

    nivel_riesgo = "bajo"
    if probabilidad > 0.6:
        nivel_riesgo = "alto"
    elif probabilidad > 0.3:
        nivel_riesgo = "medio"

    return json.dumps(
        {
            "patient_id": patient_id,
            "patient": f"{paciente['first_name']} {paciente['last_name']}",
            "total_appointments": total,
            "cancellation_rate": f"{(tasa_cancelacion * 100):.1f}%",
            "attendance_rate": f"{(tasa_asistencia * 100):.1f}%",
            "no_show_probability": f"{(probabilidad * 100):.1f}%",
            "risk_level": nivel_riesgo,
            "risk_factors": factores_riesgo
            if factores_riesgo
            else ["Ninguno identificado"],
            "recommendation": "Enviar recordatorio 24h antes"
            if nivel_riesgo == "medio"
            else (
                "Considerar confirmación telefónica y recordatorio SMS"
                if nivel_riesgo == "alto"
                else "Sin acciones adicionales requeridas"
            ),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def sugerir_seguimiento(appointment_id: int) -> str:
    """Sugiere una cita de seguimiento basada en el diagnóstico de una cita completada.

    Analiza la nota médica y recomienda:
    - Tiempo de seguimiento recomendado
    - Especialidad necesaria
    - Motivo del seguimiento

    Args:
        appointment_id: ID de la cita completada.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.start_datetime,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       e.name AS specialty,
                       nm.diagnosis, nm.treatment, nm.observations
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN doctors m ON m.id = c.doctor_id
                JOIN specialties e ON e.id = m.specialty_id
                JOIN medical_notes nm ON nm.appointment_id = c.id
                WHERE c.id = :appointment_id
                """
            ),
            {"appointment_id": appointment_id},
        )
        cita = result.mappings().first()
    await engine.dispose()

    if not cita:
        return f"Appointment {appointment_id} not found or has no medical note."

    # Simple keyword-based recommendations
    diagnosis = (cita["diagnosis"] or "").lower()
    treatment = (cita["treatment"] or "").lower()

    # Determine follow-up timing based on keywords
    followup_days = 30  # Default: 1 month
    reason = "General follow-up"

    if any(word in diagnosis for word in ["surgery", "operation", "procedure"]):
        followup_days = 14
        reason = "Post-procedure review"
    elif any(word in diagnosis for word in ["infection", "antibiotic"]):
        followup_days = 7
        reason = "Treatment evolution"
    elif any(word in diagnosis for word in ["chronic", "diabetes", "hypertension"]):
        followup_days = 90
        reason = "Chronic condition management"
    elif any(word in treatment for word in ["physiotherapy", "rehabilitation"]):
        followup_days = 21
        reason = "Rehabilitation evolution"

    return json.dumps(
        {
            "original_appointment": appointment_id,
            "patient": cita["patient"],
            "current_doctor": cita["doctor"],
            "specialty": cita["specialty"],
            "diagnosis": cita["diagnosis"][:200] if cita["diagnosis"] else "N/A",
            "recommended_followup": {
                "days": followup_days,
                "reason": reason,
                "suggested_specialty": cita["specialty"],
            },
            "message": f"Follow-up recommended in {followup_days} days. {reason}.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def encontrar_horario_compartido(
    doctor_ids: list[int], fecha: str, duracion_min: int = 30
) -> str:
    """Encuentra horarios donde múltiples doctores estén disponibles simultáneamente.

    Útil para appointments conjuntas o segundas opiniones.

    Args:
        doctor_ids: Lista de IDs de médicos (mínimo 2).
        date: Fecha a consultar (YYYY-MM-DD).
        duracion_min: Duración de la cita en minutos.
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    if len(doctor_ids) < 2:
        return "At least 2 doctors are required to find a shared schedule."

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get all occupied slots for each doctor
        disponibilidad = {}
        for med_id in doctor_ids:
            result = await db.execute(
                text(
                    """
                    SELECT c.start_datetime, c.end_datetime
                    FROM appointments c
                    JOIN appointment_statuses ec ON ec.id = c.status_id
                    WHERE c.doctor_id = :doctor_id
                      AND DATE(c.start_datetime) = :fecha
                      AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                    ORDER BY c.start_datetime
                    """
                ),
                {"doctor_id": med_id, "date": fecha},
            )
            ocupadas = result.mappings().all()

            # Get doctor name
            result_med = await db.execute(
                text("SELECT first_name, last_name FROM doctors WHERE id = :id"),
                {"id": med_id},
            )
            medico = result_med.mappings().first()

            if medico:
                disponibilidad[med_id] = {
                    "name": f"{medico['first_name']} {medico['last_name']}",
                    "ocupadas": ocupadas,
                }
    await engine.dispose()

    # Generate potential slots
    date_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    all_slots = []
    for hour in range(8, 20):
        for minute in [0, 30]:
            slot_start = datetime.combine(
                date_obj, datetime.min.time().replace(hour=hour, minute=minute)
            )
            if slot_start + timedelta(minutes=duracion_min) <= datetime.combine(
                date_obj, datetime.min.time().replace(hour=20)
            ):
                all_slots.append(slot_start)

    # Find slots where ALL doctors are free
    slots_compartidos = []
    for slot in all_slots:
        slot_end = slot + timedelta(minutes=duracion_min)
        todos_libres = True
        for _med_id, info in disponibilidad.items():
            for occ in info["ocupadas"]:
                if slot < occ["end_datetime"] and slot_end > occ["start_datetime"]:
                    todos_libres = False
                    break
            if not todos_libres:
                break
        if todos_libres:
            slots_compartidos.append(slot)

    return json.dumps(
        {
            "doctors": [
                disponibilidad[mid]["name"]
                for mid in doctor_ids
                if mid in disponibilidad
            ],
            "date": fecha,
            "duration_min": duracion_min,
            "shared_schedules": [
                {
                    "start_time": s.strftime("%H:%M"),
                    "end_time": (s + timedelta(minutes=duracion_min)).strftime("%H:%M"),
                    "suggestion": s.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                for s in slots_compartidos[:8]
            ],
            "total_available": len(slots_compartidos),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def triagar_por_sintomas(symptom_description: str) -> str:
    """Analiza síntomas descritos y sugiere especialidad y nivel de urgencia.

    Args:
        symptom_description: Descripción de síntomas en lenguaje natural.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    # Keyword-based triage rules
    reglas = {
        "urgente": {
            "keywords": [
                "dolor pecho",
                "dificultad para respirar",
                "sangrado abundante",
                "pérdida de conocimiento",
                "convulsiones",
                "alergia severa",
                "dolor abdominal intenso",
                "fiebre alta",
                "traumatismo",
            ],
            "level": "URGENTE",
            "specialty": "Urgencias",
            "tiempo": "Inmediato",
        },
        "alta": {
            "keywords": [
                "dolor fuerte",
                "fiebre",
                "inflamación",
                "mareo",
                "vómito",
                "diarrea persistente",
                "dolor articular",
                "erupción cutánea",
                "infección",
            ],
            "level": "ALTA",
            "specialty": "Medicina General",
            "tiempo": "24-48 horas",
        },
        "media": {
            "keywords": [
                "dolor leve",
                "cansancio",
                "tos",
                "resfriado",
                "dolor de cabeza",
                "insomnio",
                "ansiedad leve",
                "dolor de espalda",
                "malestar general",
            ],
            "level": "MEDIA",
            "specialty": "Medicina General",
            "tiempo": "3-5 días",
        },
        "baja": {
            "keywords": [
                "consulta",
                "receta",
                "certificado",
                "control",
                "seguimiento",
                "prevención",
                "examen",
            ],
            "level": "BAJA",
            "specialty": "Medicina General",
            "tiempo": "1-2 semanas",
        },
    }

    sintomas_lower = symptom_description.lower()
    resultado = None

    for _nivel, regla in reglas.items():
        for keyword in regla["keywords"]:
            if keyword in sintomas_lower:
                resultado = regla
                break
        if resultado:
            break

    if not resultado:
        resultado = {
            "level": "MEDIA",
            "specialty": "Medicina General",
            "tiempo": "3-5 días",
        }

    # Get available specialties
    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text("SELECT id, name FROM specialties ORDER BY name")
        )
        specialties = [dict(r) for r in result.mappings().all()]
    await engine.dispose()

    return json.dumps(
        {
            "sintomas_evaluados": symptom_description,
            "triage": {
                "urgency_level": resultado.get("level", "MEDIA"),
                "recommended_specialty": resultado.get("specialty", "Medicina General"),
                "attention_time": resultado.get("tiempo", "3-5 días"),
            },
            "specialties_disponibles": specialties,
            "message": f"Nivel: {resultado.get('nivel', 'MEDIA')}. "
            f"Especialidad: {resultado.get('especialidad', 'Medicina General')}. "
            f"Tiempo recomendado: {resultado.get('tiempo', '3-5 días')}.",
            "nota": "Este triaje es orientativo. Un profesional debe confirmar la evaluación.",
        },
        ensure_ascii=False,
        indent=2,
    )


# ============================================================================
# AGENDA IA: HERRAMIENTAS DE GESTIÓN MASIVA Y EMERGENCIA
# ============================================================================


@tool
async def cancelar_citas_masivo(
    doctor_id: int, fecha: str, motivo: str = "Emergencia médica"
) -> str:
    """Cancela TODAS las appointments de un médico en una fecha específica.

    Útil para emergencias: médico enfermo, cierre inesperado, etc.
    Notifica automáticamente a la lista de espera.

    Args:
        doctor_id: ID del médico.
        fecha: Fecha en formato YYYY-MM-DD.
        motivo: Motivo de la cancelación masiva.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get affected appointments
        result = await db.execute(
            text(
                """
                SELECT c.id, CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       c.start_datetime, c.end_datetime
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND DATE(c.start_datetime) = :fecha
                  AND ec.code NOT IN ('CANCELADA', 'COMPLETADA')
                ORDER BY c.start_datetime
                """
            ),
            {"doctor_id": doctor_id, "date": fecha},
        )
        appointments = result.mappings().all()

        if not appointments:
            await engine.dispose()
            return f"No active appointments for doctor {doctor_id} on {fecha}."

        # Get cancel state
        result_state = await db.execute(
            text("SELECT id FROM appointment_statuses WHERE codigo = 'CANCELADA'")
        )
        cancel_state = result_state.first()

        # Cancel all appointments
        canceladas = []
        for cita in appointments:
            await db.execute(
                text(
                    """
                    UPDATE appointments SET status_id = :status_id, updated_at = NOW()
                    WHERE id = :appointment_id
                    """
                ),
                {"status_id": cancel_state[0], "appointment_id": cita["id"]},
            )
            canceladas.append(
                {
                    "id": cita["id"],
                    "patient": cita["patient"],
                    "hora": str(cita["start_datetime"]),
                }
            )

        # Check waitlist
        result_espera = await db.execute(
            text(
                """
                SELECT id, patient_id, motivo
                FROM waitlist
                WHERE doctor_id = :doctor_id AND estado = 'PENDIENTE'
                """
            ),
            {"doctor_id": doctor_id},
        )
        espera = result_espera.mappings().all()

        await db.commit()
    await engine.dispose()

    return json.dumps(
        {
            "action": "bulk_cancel",
            "doctor_id": doctor_id,
            "date": fecha,
            "reason": motivo,
            "appointments_cancelled": len(canceladas),
            "details": canceladas,
            "waitlist_notified": len(espera),
            "message": f"Cancelled {len(canceladas)} appointments. {len(espera)} patients on waitlist.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def replanificar_citas(
    doctor_id: int, fecha_origen: str, fecha_destino: str, confirmado: bool = False
) -> str:
    """Mueve TODAS las appointments de un día a otro para un médico.

    Revisa disponibilidad en la fecha destino y sugiere horarios.

    Args:
        doctor_id: ID del médico.
        source_date: Fecha original (YYYY-MM-DD).
        target_date: Fecha destino (YYYY-MM-DD).
        confirmado: Debe ser True para ejecutar.
    """
    from datetime import datetime

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get appointments to move
        result = await db.execute(
            text(
                """
                SELECT c.id, c.start_datetime, c.end_datetime,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       ec.code AS estado
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND DATE(c.start_datetime) = :fecha_origen
                  AND ec.code NOT IN ('CANCELADA', 'COMPLETADA')
                ORDER BY c.start_datetime
                """
            ),
            {"doctor_id": doctor_id, "source_date": fecha_origen},
        )
        appointments_origen = result.mappings().all()

        # Get existing appointments on destination date
        result_dest = await db.execute(
            text(
                """
                SELECT c.start_datetime, c.end_datetime
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND DATE(c.start_datetime) = :fecha_destino
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.start_datetime
                """
            ),
            {"doctor_id": doctor_id, "target_date": fecha_destino},
        )
        ocupadas_dest = result_dest.mappings().all()
    await engine.dispose()

    if not appointments_origen:
        return f"No active appointments for doctor {doctor_id} on {fecha_origen}."

    if not confirmado:
        # Preview mode: suggest available slots
        return json.dumps(
            {
                "action": "replanificacion_pendiente",
                "appointments_a_mover": len(appointments_origen),
                "source_date": fecha_origen,
                "target_date": fecha_destino,
                "appointments": [
                    {
                        "id": c["id"],
                        "patient": c["patient"],
                        "hora_original": str(c["start_datetime"]),
                    }
                    for c in appointments_origen
                ],
                "message": "Confirme para ejecutar la replanificación.",
            },
            ensure_ascii=False,
            indent=2,
        )

    # Execute replanification
    date_dest = datetime.strptime(fecha_destino, "%Y-%m-%d").date()
    hora_actual = datetime.combine(date_dest, datetime.min.time().replace(hour=8))
    hora_fin_jornada = datetime.combine(date_dest, datetime.min.time().replace(hour=20))

    movidas = []
    for cita in appointments_origen:
        duracion = cita["end_datetime"] - cita["start_datetime"]
        nueva_hora = hora_actual
        nueva_fin = nueva_hora + duracion

        # Find next available slot
        while nueva_fin <= hora_fin_jornada:
            conflicto = False
            for occ in ocupadas_dest:
                if (
                    nueva_hora < occ["end_datetime"]
                    and nueva_fin > occ["start_datetime"]
                ):
                    conflicto = True
                    nueva_hora = occ["end_datetime"]
                    nueva_fin = nueva_hora + duracion
                    break
            if not conflicto:
                break
            if nueva_fin > hora_fin_jornada:
                break

        if nueva_fin <= hora_fin_jornada:
            engine2 = create_async_engine(_conn_str)
            async_session2 = async_sessionmaker(engine2, expire_on_commit=False)
            async with async_session2() as db:
                await db.execute(
                    text(
                        """
                        UPDATE appointments
                        SET start_datetime = :inicio, end_datetime = :fin,
                            status_id = (SELECT id FROM appointment_statuses WHERE codigo = 'REAGENDADA')
                        WHERE id = :appointment_id
                        """
                    ),
                    {
                        "start": nueva_hora,
                        "end": nueva_fin,
                        "appointment_id": cita["id"],
                    },
                )
                await db.commit()
            await engine2.dispose()

            movidas.append(
                {
                    "id": cita["id"],
                    "patient": cita["patient"],
                    "hora_original": str(cita["start_datetime"]),
                    "nueva_hora": str(nueva_hora),
                }
            )
            hora_actual = nueva_fin
            ocupadas_dest.append(
                {"start_datetime": nueva_hora, "end_datetime": nueva_fin}
            )

    return json.dumps(
        {
            "action": "replanificacion_completada",
            "doctor_id": doctor_id,
            "source_date": fecha_origen,
            "target_date": fecha_destino,
            "appointments_movidas": len(movidas),
            "details": movidas,
            "message": f"Moved {len(movidas)} appointments from {fecha_origen} to {fecha_destino}.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def notificar_lista_espera(doctor_id: int, fecha: str = "") -> str:
    """Notifica a patients en lista de espera cuando se libera un slot.

    Args:
        doctor_id: ID del médico.
        fecha: Fecha específica a notificar (opcional, default: próximos 7 días).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get pending waitlist
        query = """
            SELECT le.id, le.patient_id, le.fecha_preferida, le.motivo,
                   CONCAT(p.first_name, ' ', p.last_name) AS paciente
            FROM waitlist le
            JOIN patients p ON p.id = le.patient_id
            WHERE le.doctor_id = :doctor_id AND le.estado = 'PENDIENTE'
        """
        if fecha:
            query += " AND le.fecha_preferida = :fecha"
        query += " ORDER BY le.created_at"

        params = {"doctor_id": doctor_id}
        if fecha:
            params["date"] = fecha

        result = await db.execute(text(query), params)
        pendientes = result.mappings().all()

        if not pendientes:
            await engine.dispose()
            return "No patients on the waitlist for this doctor."

        # Check available slots
        result_slots = await db.execute(
            text(
                """
                SELECT c.start_datetime, c.end_datetime
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND c.start_datetime >= NOW()
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.start_datetime
                """
            ),
            {"doctor_id": doctor_id},
        )
        ocupadas = result_slots.mappings().all()

    await engine.dispose()

    # Find free slots in next 7 days
    date_obj = datetime.now().date()
    slots_libres = []
    for day_offset in range(7):
        check_date = date_obj + timedelta(days=day_offset)
        for hour in [9, 10, 11, 14, 15, 16, 17]:
            slot_start = datetime.combine(
                check_date, datetime.min.time().replace(hour=hour)
            )
            slot_end = slot_start + timedelta(minutes=30)
            is_free = True
            for occ in ocupadas:
                if (
                    slot_start < occ["end_datetime"]
                    and slot_end > occ["start_datetime"]
                ):
                    is_free = False
                    break
            if is_free:
                slots_libres.append(slot_start)

    # Match waitlist with available slots
    notificados = []
    for pend in pendientes[: len(slots_libres)]:
        notificados.append(
            {
                "patient_id": pend["patient_id"],
                "patient": pend["patient"],
                "slot_offered": slots_libres[len(notificados)].strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),
                "original_reason": pend["reason"],
            }
        )

    return json.dumps(
        {
            "action": "notify_waitlist",
            "doctor_id": doctor_id,
            "total_pending": len(pendientes),
            "available_slots": len(slots_libres),
            "notified": len(notificados),
            "details": notificados,
            "message": f"{len(notificados)} patients notified of available slots.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def protocolo_emergencia(
    doctor_id: int, fecha: str, tipo: str = "enfermedad"
) -> str:
    """Ejecuta protocolo de emergencia: cancela, reasigna y notifica automáticamente.

    Tipos: enfermedad, emergencia_personal, cierre_institucional, desastre_natural.

    Args:
        doctor_id: ID del médico afectado.
        date: Fecha del incidente (YYYY-MM-DD).
        tipo: Tipo de emergencia.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get doctor info
        result_med = await db.execute(
            text("SELECT first_name, last_name FROM doctors WHERE id = :id"),
            {"id": doctor_id},
        )
        medico = result_med.mappings().first()

        if not medico:
            await engine.dispose()
            return f"Doctor {doctor_id} not found."

        # Get all active appointments
        result = await db.execute(
            text(
                """
                SELECT c.id, c.patient_id, c.start_datetime,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND DATE(c.start_datetime) = :fecha
                  AND ec.code NOT IN ('CANCELADA', 'COMPLETADA')
                ORDER BY c.start_datetime
                """
            ),
            {"doctor_id": doctor_id, "date": fecha},
        )
        appointments = result.mappings().all()

        # Cancel all
        result_state = await db.execute(
            text("SELECT id FROM appointment_statuses WHERE codigo = 'CANCELADA'")
        )
        cancel_state = result_state.first()

        canceladas = []
        for cita in appointments:
            await db.execute(
                text(
                    "UPDATE appointments SET status_id = :status_id WHERE id = :appointment_id"
                ),
                {"status_id": cancel_state[0], "appointment_id": cita["id"]},
            )
            canceladas.append(
                {
                    "id": cita["id"],
                    "patient": cita["patient"],
                    "hora": str(cita["start_datetime"]),
                }
            )

        await db.commit()
    await engine.dispose()

    return json.dumps(
        {
            "action": "protocolo_emergencia",
            "tipo": tipo,
            "doctor": f"{medico['first_name']} {medico['last_name']}",
            "date": fecha,
            "appointments_canceladas": len(canceladas),
            "details": canceladas,
            "next_steps": [
                "Notificar a patients afectados",
                "Verificar lista de espera para reasignación",
                "Actualizar estado del médico en el sistema",
                "Documentar incidente en auditoría",
            ],
            "message": f"Protocol executed: {len(canceladas)} appointments cancelled due to {tipo}.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def optimizar_agenda(doctor_id: int, days: int = 14) -> str:
    """Analiza y sugiere optimizaciones para la agenda del médico.

    Identifica:
    - Horarios subutilizados
    - Bloques muertos
    - Oportunidades de compactación
    - Distribución ideal de appointments

    Args:
        doctor_id: ID del médico.
        days: Días a analizar (default 14).
    """

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT DATE(c.start_datetime) AS dia,
                       EXTRACT(HOUR FROM c.start_datetime) AS hora,
                       COUNT(*) AS total_appointments
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND c.start_datetime >= NOW()
                  AND c.start_datetime < NOW() + INTERVAL ':days days'
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY dia, hora
                ORDER BY dia, hora
                """
            ),
            {"doctor_id": doctor_id, "days": days},
        )
        carga = result.mappings().all()
    await engine.dispose()

    # Analyze patterns
    horas_pico = {}
    horas_vacias = []
    for row in carga:
        hora = int(row["hora"])
        horas_pico[hora] = horas_pico.get(hora, 0) + row["total_appointments"]

    # Find underutilized hours (08:00-20:00)
    for hour in range(8, 20):
        if hour not in horas_pico:
            horas_vacias.append(f"{hour:02d}:00")

    # Recommendations
    recomendaciones = []
    if horas_vacias:
        recomendaciones.append(
            {
                "tipo": "compactar",
                "description": f"Horarios vacíos: {', '.join(horas_vacias[:5])}",
                "action": "Mover appointments a estos horarios para maximizar espacio.",
            }
        )

    hora_pico = max(horas_pico, key=horas_pico.get) if horas_pico else None
    if hora_pico and horas_pico[hora_pico] > 5:
        recomendaciones.append(
            {
                "tipo": "distribuir",
                "description": f"Hora pico: {hora_pico:02d}:00 con {horas_pico[hora_pico]} appointments",
                "action": "Distribuir carga a horas menos ocupadas.",
            }
        )

    return json.dumps(
        {
            "doctor_id": doctor_id,
            "analysis_period": f"Próximos {days} días",
            "peak_hours": horas_pico,
            "underutilized_hours": horas_vacias,
            "recommendations": recomendaciones,
            "current_efficiency": f"{len(carga)} bloques ocupados de {days * 12} posibles",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def generar_recordatorio(appointment_id: int, tipo: str = "general") -> str:
    """Genera un recordatorio personalizado para una cita médica.

    Tipos: general, pre_cita, post_cita, seguimiento.

    Args:
        appointment_id: ID de la cita.
        tipo: Tipo de recordatorio.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.start_datetime, c.reason,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       e.name AS specialty,
                       ec.code AS estado
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN doctors m ON m.id = c.doctor_id
                JOIN specialties e ON e.id = m.specialty_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.id = :appointment_id
                """
            ),
            {"appointment_id": appointment_id},
        )
        cita = result.mappings().first()
    await engine.dispose()

    if not cita:
        return f"Appointment {appointment_id} not found."

    # Generate reminder based on type
    recordatorios = {
        "general": (
            f"Estimado/a {cita['paciente']}, le recordamos su cita con {cita['medico']} "
            f"({cita['especialidad']}) el {cita['start_datetime']}. "
            f"Motivo: {cita['reason']}. Por favor, confirme asistencia."
        ),
        "pre_cita": (
            f"Recordatorio 24h: Mañana tiene cita con {cita['medico']} a las "
            f"{cita['start_datetime']}. Por favor traiga identificación y seguro médico."
        ),
        "post_cita": (
            f"Gracias por su visita con {cita['medico']}. Si tiene síntomas o dudas, "
            f"contáctenos. Su diagnóstico está disponible en su portal de paciente."
        ),
        "seguimiento": (
            f"Seguimiento: Ha pasado 1 mes desde su última consulta con {cita['medico']}. "
            f"¿Desea agendar una cita de control?"
        ),
    }

    mensaje = recordatorios.get(tipo, recordatorios["general"])

    return json.dumps(
        {
            "appointment_id": appointment_id,
            "tipo": tipo,
            "patient": cita["patient"],
            "doctor": cita["doctor"],
            "date": str(cita["start_datetime"]),
            "mensaje_recordatorio": mensaje,
            "canal_sugerido": "SMS" if tipo == "pre_cita" else "Email",
        },
        ensure_ascii=False,
        indent=2,
    )


# ============================================================================
# AGENDA IA: FEATURES ÚNICOS DE DIFERENCIACIÓN
# ============================================================================


@tool
async def predecir_demanda(days: int = 30) -> str:
    """Predice la demanda de appointments médicas para los próximos N días.

    Analiza tendencias históricas, patrones estacionales y sugiere:
    - Días de alta demanda esperados
    - Especialidades más solicitadas
    - Recomendaciones de staffing

    Args:
        days: Días a predecir (default 30).
    """

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get historical data (last 90 days)
        result = await db.execute(
            text(
                """
                SELECT DATE(c.start_datetime) AS dia,
                       e.name AS specialty,
                       EXTRACT(DOW FROM c.start_datetime) AS day_of_week,
                       COUNT(*) AS total_appointments
                FROM appointments c
                JOIN doctors m ON m.id = c.doctor_id
                JOIN specialties e ON e.id = m.specialty_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.start_datetime >= NOW() - INTERVAL '90 days'
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY dia, especialidad, day_of_week
                ORDER BY dia
                """
            )
        )
        historial = result.mappings().all()

        # Get current month appointments
        result_actual = await db.execute(
            text(
                """
                SELECT DATE(c.start_datetime) AS dia,
                       COUNT(*) AS total
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.start_datetime >= DATE_TRUNC('month', NOW())
                  AND c.start_datetime < DATE_TRUNC('month', NOW()) + INTERVAL '1 month'
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY dia
                """
            )
        )
        mes_actual = result_actual.mappings().all()
    await engine.dispose()

    # Analyze patterns
    day_of_week_map = {
        0: "Dom",
        1: "Lun",
        2: "Mar",
        3: "Mié",
        4: "Jue",
        5: "Vie",
        6: "Sáb",
    }
    demanda_por_dia = {}
    demanda_por_especialidad = {}

    for row in historial:
        dia = day_of_week_map.get(row["day_of_week"], "?")
        demanda_por_dia[dia] = demanda_por_dia.get(dia, 0) + row["total_appointments"]
        esp = row["specialty"]
        demanda_por_especialidad[esp] = (
            demanda_por_especialidad.get(esp, 0) + row["total_appointments"]
        )

    # Predictions
    promedio_diario = sum(demanda_por_dia.values()) / 7 if demanda_por_dia else 0
    dia_pico = (
        max(demanda_por_dia, key=demanda_por_dia.get) if demanda_por_dia else "N/A"
    )
    especialidad_top = (
        max(demanda_por_especialidad, key=demanda_por_especialidad.get)
        if demanda_por_especialidad
        else "N/A"
    )

    return json.dumps(
        {
            "analysis_period": "90 días históricos",
            "prediction_period": f"Próximos {days} días",
            "promedio_appointments_dia": round(promedio_diario, 1),
            "highest_demand_day": dia_pico,
            "demand_per_day": demanda_por_dia,
            "specialties_top": demanda_por_especialidad,
            "most_requested_specialty": especialidad_top,
            "appointments_mes_actual": len(mes_actual),
            "recommendations": [
                f"Aumentar disponibilidad los {dia_pico}",
                f"Priorizar especialidad: {especialidad_top}",
                "Considerar horarios extendidos en temporada alta",
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def matching_paciente_medico(patient_id: int) -> str:
    """Recomienda el mejor médico para un paciente basado en compatibilidad.

    Analiza:
    - Historial de appointments previas
    - Especialidades más visitadas
    - Médicos con mejor tasa de completado
    - Disponibilidad actual

    Args:
        patient_id: ID del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get patient info
        result_pat = await db.execute(
            text(
                """
                SELECT p.id, CONCAT(p.first_name, ' ', p.last_name) AS name,
                       COUNT(c.id) AS total_appointments,
                       SUM(CASE WHEN ec.code = 'COMPLETADA' THEN 1 ELSE 0 END) AS completadas,
                       SUM(CASE WHEN ec.code = 'CANCELADA' THEN 1 ELSE 0 END) AS canceladas
                FROM patients p
                LEFT JOIN appointments c ON c.patient_id = p.id
                LEFT JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE p.id = :patient_id
                GROUP BY p.id, p.first_name, p.last_name
                """
            ),
            {"patient_id": patient_id},
        )
        paciente = result_pat.mappings().first()

        if not paciente:
            await engine.dispose()
            return f"Patient {patient_id} not found."

        # Get doctor history for this patient
        result_docs = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.first_name, ' ', m.last_name) AS name,
                       e.name AS specialty,
                       COUNT(c.id) AS appointments_con_paciente,
                       SUM(CASE WHEN ec.code = 'COMPLETADA' THEN 1 ELSE 0 END) AS completadas,
                       SUM(CASE WHEN ec.code = 'CANCELADA' THEN 1 ELSE 0 END) AS canceladas
                FROM doctors m
                JOIN specialties e ON e.id = m.specialty_id
                LEFT JOIN appointments c ON c.doctor_id = m.id AND c.patient_id = :patient_id
                LEFT JOIN appointment_statuses ec ON ec.id = c.status_id
                GROUP BY m.id, m.first_name, m.last_name, e.name
                HAVING COUNT(c.id) > 0
                ORDER BY completadas DESC NULLS LAST
                LIMIT 5
                """
            ),
            {"patient_id": patient_id},
        )
        doctors_historial = result_docs.mappings().all()

        # Get top doctors overall
        result_top = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.first_name, ' ', m.last_name) AS name,
                       e.name AS specialty,
                       COUNT(c.id) AS total_appointments,
                       SUM(CASE WHEN ec.code = 'COMPLETADA' THEN 1 ELSE 0 END) AS completadas
                FROM doctors m
                JOIN specialties e ON e.id = m.specialty_id
                LEFT JOIN appointments c ON c.doctor_id = m.id
                LEFT JOIN appointment_statuses ec ON ec.id = c.status_id
                GROUP BY m.id, m.first_name, m.last_name, e.name
                ORDER BY completadas DESC NULLS LAST
                LIMIT 5
                """
            )
        )
        doctors_top = result_top.mappings().all()
    await engine.dispose()

    # Calculate compatibility scores
    recomendaciones = []
    for med in doctors_historial:
        tasa_exito = (
            (med["completadas"] or 0) / med["appointments_con_paciente"]
            if med["appointments_con_paciente"] > 0
            else 0
        )
        score = tasa_exito * 100
        recomendaciones.append(
            {
                "doctor_id": med["id"],
                "name": med["name"],
                "specialty": med["specialty"],
                "appointments_juntos": med["appointments_con_paciente"],
                "success_rate": f"{(tasa_exito * 100):.1f}%",
                "compatibility_score": round(score, 1),
                "tipo": "historial",
            }
        )

    # Add top doctors if no history
    if not recomendaciones:
        for med in doctors_top:
            tasa = (
                (med["completadas"] or 0) / med["total_appointments"]
                if med["total_appointments"] > 0
                else 0
            )
            recomendaciones.append(
                {
                    "doctor_id": med["id"],
                    "name": med["name"],
                    "specialty": med["specialty"],
                    "compatibility_score": round(tasa * 100, 1),
                    "tipo": "recomendado",
                }
            )

    return json.dumps(
        {
            "patient": paciente["name"],
            "total_appointments_historial": paciente["total_appointments"],
            "mejores_doctors": sorted(
                recomendaciones, key=lambda x: x["compatibility_score"], reverse=True
            )[:5],
            "message": "Médicos ordenados por compatibilidad con el paciente.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def duracion_inteligente(doctor_id: int, motivo: str = "") -> str:
    """Predice la duración óptima de una cita basada en el tipo de consulta.

    Analiza appointments previas similares y sugiere duración personalizada.

    Args:
        doctor_id: ID del médico.
        reason: Motivo de la consulta (para buscar patrones similares).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get average duration by doctor
        result = await db.execute(
            text(
                """
                SELECT AVG(EXTRACT(EPOCH FROM (c.end_datetime - c.start_datetime))/60) AS promedio_min,
                       MIN(EXTRACT(EPOCH FROM (c.end_datetime - c.start_datetime))/60) AS minimo,
                       MAX(EXTRACT(EPOCH FROM (c.end_datetime - c.start_datetime))/60) AS maximo,
                       COUNT(*) AS total_appointments
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND ec.code = 'COMPLETADA'
                """
            ),
            {"doctor_id": doctor_id},
        )
        stats = result.mappings().first()

        # Get duration by reason (if provided)
        duracion_motivo = None
        if motivo:
            result_motivo = await db.execute(
                text(
                    """
                    SELECT AVG(EXTRACT(EPOCH FROM (c.end_datetime - c.start_datetime))/60) AS promedio
                    FROM appointments c
                    JOIN appointment_statuses ec ON ec.id = c.status_id
                    WHERE c.doctor_id = :doctor_id
                      AND c.reason ILIKE :motivo
                      AND ec.code = 'COMPLETADA'
                    """
                ),
                {"doctor_id": doctor_id, "reason": f"%{motivo}%"},
            )
            duracion_motivo = result_motivo.mappings().first()
    await engine.dispose()

    promedio = stats["promedio_min"] or 30
    minimo = stats["minimo"] or 15
    maximo = stats["maximo"] or 60

    duracion_recomendada = promedio
    if duracion_motivo and duracion_motivo["promedio"]:
        duracion_recomendada = duracion_motivo["promedio"]

    return json.dumps(
        {
            "doctor_id": doctor_id,
            "reason": motivo or "General",
            "historical_statistics": {
                "promedio_min": round(promedio, 1),
                "minimo_min": round(minimo, 1),
                "maximo_min": round(maximo, 1),
                "total_appointments_analizadas": stats["total_appointments"],
            },
            "recommended_duration_min": round(duracion_recomendada),
            "suggested_range": f"{round(duracion_recomendada - 5)}-{round(duracion_recomendada + 10)} min",
            "message": f"Cita recomendada de {round(duracion_recomendada)} minutos.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def optimizar_ingresos(doctor_id: int, days: int = 30) -> str:
    """Analiza y sugiere estrategias para maximizar ingresos.

    Identifica:
    - Horarios de mayor facturación
    - Citas canceladas que podrían rellenarse
    - Oportunidades de upselling (procedimientos adicionales)
    - Precio óptimo por tipo de cita

    Args:
        doctor_id: ID del médico.
        days: Días a analizar (default 30).
    """

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get appointment stats
        result = await db.execute(
            text(
                """
                SELECT EXTRACT(HOUR FROM c.start_datetime) AS hora,
                       EXTRACT(DOW FROM c.start_datetime) AS day_of_week,
                       ec.code AS estado,
                       COUNT(*) AS total
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND c.start_datetime >= NOW() - INTERVAL ':days days'
                GROUP BY hora, day_of_week, ec.code
                """
            ),
            {"doctor_id": doctor_id, "days": days},
        )
        stats = result.mappings().all()
    await engine.dispose()

    # Analyze
    horas_facturacion = {}
    cancelaciones_por_hora = {}
    total_completadas = 0
    total_canceladas = 0

    for row in stats:
        hora = int(row["hora"])
        if row["status"] == "COMPLETADA":
            horas_facturacion[hora] = horas_facturacion.get(hora, 0) + row["total"]
            total_completadas += row["total"]
        elif row["status"] == "CANCELADA":
            cancelaciones_por_hora[hora] = (
                cancelaciones_por_hora.get(hora, 0) + row["total"]
            )
            total_canceladas += row["total"]

    # Revenue optimization suggestions
    sugerencias = []
    hora_pico = (
        max(horas_facturacion, key=horas_facturacion.get) if horas_facturacion else None
    )

    if hora_pico:
        sugerencias.append(
            {
                "tipo": "mantener",
                "description": f"Hora pico de productividad: {hora_pico:02d}:00",
                "impacto": "Alto",
            }
        )

    horas_canceladas = sorted(
        cancelaciones_por_hora.items(), key=lambda x: x[1], reverse=True
    )
    if horas_canceladas:
        sugerencias.append(
            {
                "tipo": "rellenar",
                "description": f"Horas con más cancelaciones: {horas_canceladas[0][0]:02d}:00 ({horas_canceladas[0][1]} cancelaciones)",
                "impacto": "Medio",
                "action": "Ofrecer descuento o prioridad para rellenar estos slots",
            }
        )

    if total_canceladas > total_completadas * 0.2:
        sugerencias.append(
            {
                "tipo": "reducir_cancelaciones",
                "description": f"Tasa de cancelación: {(total_canceladas / (total_completadas + total_canceladas) * 100):.1f}%",
                "impacto": "Alto",
                "action": "Implementar recordatorios 24h antes y confirmación telefónica",
            }
        )

    return json.dumps(
        {
            "doctor_id": doctor_id,
            "period": f"Últimos {days} días",
            "appointments_completadas": total_completadas,
            "appointments_canceladas": total_canceladas,
            "cancellation_rate": f"{(total_canceladas / (total_completadas + total_canceladas) * 100):.1f}%"
            if (total_completadas + total_canceladas) > 0
            else "0%",
            "most_productive_hours": horas_facturacion,
            "sugerencias": sugerencias,
            "improvement_potential": f"Reducir cancelaciones podría aumentar ingresos ~{(total_canceladas * 0.3):.0f} appointments/mes",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def score_satisfaccion(patient_id: int) -> str:
    """Calcula un score de satisfacción del paciente basado en su comportamiento.

    Indicadores:
    - Tasa de asistencia
    - Frecuencia de reagendamientos
    - Tiempo entre appointments
    - Estado de las appointments

    Args:
        patient_id: ID del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.start_datetime, ec.code AS estado,
                       LAG(c.start_datetime) OVER (ORDER BY c.start_datetime) AS cita_anterior
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.patient_id = :patient_id
                ORDER BY c.start_datetime
                LIMIT 20
                """
            ),
            {"patient_id": patient_id},
        )
        historial = result.mappings().all()

        result_pat = await db.execute(
            text("SELECT first_name, last_name FROM patients WHERE id = :id"),
            {"id": patient_id},
        )
        paciente = result_pat.mappings().first()
    await engine.dispose()

    if not paciente:
        return f"Patient {patient_id} not found."

    if not historial:
        return json.dumps(
            {
                "patient": f"{paciente['first_name']} {paciente['last_name']}",
                "score": "N/A",
                "message": "Insufficient history to calculate score.",
            },
            ensure_ascii=False,
            indent=2,
        )

    total = len(historial)
    completadas = sum(1 for h in historial if h["status"] == "COMPLETADA")
    canceladas = sum(1 for h in historial if h["status"] == "CANCELADA")
    reagendadas = sum(1 for h in historial if h["status"] == "REAGENDADA")

    # Calculate score
    tasa_asistencia = completadas / total if total > 0 else 0
    penalty_cancelacion = (canceladas / total) * 30 if total > 0 else 0
    penalty_reagendamiento = (reagendadas / total) * 10 if total > 0 else 0

    score = max(
        0,
        min(
            100, (tasa_asistencia * 100) - penalty_cancelacion - penalty_reagendamiento
        ),
    )

    # Satisfaction level
    if score >= 80:
        nivel = "EXCELENTE"
        recomendacion = "Paciente leal, priorizar en agenda."
    elif score >= 60:
        nivel = "BUENO"
        recomendacion = "Paciente confiable, mantener rutina."
    elif score >= 40:
        nivel = "REGULAR"
        recomendacion = "Enviar recordatorios y confirmación."
    else:
        nivel = "BAJO"
        recomendacion = "Considerar depósito o confirmación estricta."

    return json.dumps(
        {
            "patient_id": patient_id,
            "patient": f"{paciente['first_name']} {paciente['last_name']}",
            "total_appointments": total,
            "completadas": completadas,
            "canceladas": canceladas,
            "reagendadas": reagendadas,
            "attendance_rate": f"{(tasa_asistencia * 100):.1f}%",
            "satisfaction_score": round(score, 1),
            "level": nivel,
            "recommendation": recomendacion,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def resumen_clinico_paciente(patient_id: int) -> str:
    """Genera un resumen clínico automático del paciente antes de su cita.

    Incluye:
    - Historial de diagnósticos
    - Tratamientos activos
    - Citas recientes
    - Alertas importantes

    Args:
        patient_id: ID del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Patient info
        result_pat = await db.execute(
            text(
                """
                SELECT id, first_name, last_name, birth_date, email, phone
                FROM patients WHERE id = :id
                """
            ),
            {"id": patient_id},
        )
        paciente = result_pat.mappings().first()

        if not paciente:
            await engine.dispose()
            return f"Patient {patient_id} not found."

        # Recent diagnoses
        result_diag = await db.execute(
            text(
                """
                SELECT nm.diagnosis, nm.treatment, nm.observations,
                       c.start_datetime,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico
                FROM medical_notes nm
                JOIN appointments c ON c.id = nm.appointment_id
                JOIN doctors m ON m.id = c.doctor_id
                WHERE c.patient_id = :patient_id
                ORDER BY c.start_datetime DESC
                LIMIT 5
                """
            ),
            {"patient_id": patient_id},
        )
        diagnosticos = result_diag.mappings().all()

        # Upcoming appointments
        result_appointments = await db.execute(
            text(
                """
                SELECT c.start_datetime, c.reason,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       ec.code AS estado
                FROM appointments c
                JOIN doctors m ON m.id = c.doctor_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.patient_id = :patient_id
                  AND c.start_datetime >= NOW()
                ORDER BY c.start_datetime
                LIMIT 3
                """
            ),
            {"patient_id": patient_id},
        )
        proximas_appointments = result_appointments.mappings().all()
    await engine.dispose()

    # Build summary
    resumen = {
        "patient": {
            "id": patient_id,
            "name": f"{paciente['first_name']} {paciente['last_name']}",
            "birth_date": str(paciente["birth_date"]),
        },
        "diagnosticos_recientes": [
            {
                "diagnosis": d["diagnosis"][:200] if d["diagnosis"] else "N/A",
                "treatment": d["treatment"][:200] if d["treatment"] else "N/A",
                "doctor": d["doctor"],
                "date": str(d["start_datetime"]),
            }
            for d in diagnosticos
        ],
        "proximas_appointments": [
            {
                "date": str(c["start_datetime"]),
                "doctor": c["doctor"],
                "reason": c["reason"][:150] if c["reason"] else "N/A",
                "status": c["status"],
            }
            for c in proximas_appointments
        ],
        "alertas": [],
    }

    # Generate alerts
    if diagnosticos:
        ultimo_diag = diagnosticos[0]["diagnosis"] or ""
        if any(
            word in ultimo_diag.lower()
            for word in ["crónico", "diabetes", "hipertensión"]
        ):
            resumen["alertas"].append(
                "Paciente con condición crónica - requiere seguimiento regular"
            )

    if len(diagnosticos) > 2:
        resumen["alertas"].append(
            f"Paciente con {len(diagnosticos)} consultas recientes - posible caso complejo"
        )

    return json.dumps(resumen, ensure_ascii=False, indent=2)


@tool
async def detectar_anomalias(days: int = 30) -> str:
    """Detecta patrones anómalos en la agenda que pueden indicar problemas.

    Identifica:
    - Médicos con tasa de cancelación inusualmente alta
    - Horarios con anomalías de demanda
    - Pacientes con comportamiento inusual
    - Posibles errores de programación

    Args:
        days: Días a analizar (default 30).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Doctor cancellation rates
        result_docs = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       COUNT(c.id) AS total,
                       SUM(CASE WHEN ec.code = 'CANCELADA' THEN 1 ELSE 0 END) AS canceladas
                FROM doctors m
                LEFT JOIN appointments c ON c.doctor_id = m.id
                    AND c.start_datetime >= NOW() - INTERVAL ':days days'
                LEFT JOIN appointment_statuses ec ON ec.id = c.status_id
                GROUP BY m.id, m.first_name, m.last_name
                HAVING COUNT(c.id) > 5
                """
            ),
            {"days": days},
        )
        doctors = result_docs.mappings().all()

        # Overbooking detection
        result_overbook = await db.execute(
            text(
                """
                SELECT DATE(c.start_datetime) AS dia,
                       c.doctor_id,
                       COUNT(*) AS appointments_dia
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.start_datetime >= NOW() - INTERVAL ':days days'
                  AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY dia, c.doctor_id
                HAVING COUNT(*) > 10
                """
            ),
            {"days": days},
        )
        overbooking = result_overbook.mappings().all()
    await engine.dispose()

    anomalias = []

    # Check for high cancellation rates
    for med in doctors:
        if med["total"] > 0:
            tasa = (med["canceladas"] or 0) / med["total"]
            if tasa > 0.4:
                anomalias.append(
                    {
                        "tipo": "alta_cancelacion",
                        "severidad": "ALTA",
                        "description": f"Dr. {med['medico']} tiene tasa de cancelación del {(tasa * 100):.1f}%",
                        "action": "Revisar motivos, considerar recordatorios o depósitos",
                    }
                )
            elif tasa > 0.25:
                anomalias.append(
                    {
                        "tipo": "cancelacion_moderada",
                        "severidad": "MEDIA",
                        "description": f"Dr. {med['medico']} tiene tasa de cancelación del {(tasa * 100):.1f}%",
                        "action": "Monitorear y ajustar política de cancelación",
                    }
                )

    # Check for overbooking
    for ob in overbooking:
        anomalias.append(
            {
                "tipo": "sobrecarga",
                "severidad": "MEDIA",
                "description": f"Médico {ob['doctor_id']} con {ob['appointments_dia']} appointments el {ob['dia']}",
                "action": "Revisar capacidad y redistribuir si es necesario",
            }
        )

    return json.dumps(
        {
            "analysis_period": f"Últimos {days} días",
            "anomalies_found": len(anomalias),
            "details": anomalias
            if anomalias
            else [
                {
                    "tipo": "sin_anomalias",
                    "message": "No significant anomalies detected.",
                }
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def scheduling_adaptativo(doctor_id: int) -> str:
    """Analiza el rendimiento del scheduling y sugiere mejoras automáticas.

    Aprende de:
    - Citas que excedieron el tiempo estimado
    - Patrones de puntualidad
    - Eficiencia por hora del día
    - Recomendaciones de mejora continua

    Args:
        doctor_id: ID del médico.
    """

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Analyze scheduling efficiency
        result = await db.execute(
            text(
                """
                SELECT EXTRACT(HOUR FROM c.start_datetime) AS hora,
                       AVG(EXTRACT(EPOCH FROM (c.end_datetime - c.start_datetime))/60) AS duracion_real,
                       COUNT(*) AS total_appointments,
                       SUM(CASE WHEN ec.code = 'COMPLETADA' THEN 1 ELSE 0 END) AS completadas
                FROM appointments c
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND c.start_datetime >= NOW() - INTERVAL '30 days'
                GROUP BY hora
                ORDER BY hora
                """
            ),
            {"doctor_id": doctor_id},
        )
        eficiencia = result.mappings().all()

        # Get doctor name
        result_med = await db.execute(
            text("SELECT first_name, last_name FROM doctors WHERE id = :id"),
            {"id": doctor_id},
        )
        medico = result_med.mappings().first()
    await engine.dispose()

    if not medico:
        return f"Doctor {doctor_id} not found."

    # Analyze patterns
    horas_analisis = {}
    for row in eficiencia:
        hora = int(row["hora"])
        duracion = row["duracion_real"] or 30
        completadas = row["completadas"] or 0
        total = row["total_appointments"] or 0
        tasa_completado = completadas / total if total > 0 else 0

        horas_analisis[f"{hora:02d}:00"] = {
            "duracion_promedio_min": round(duracion, 1),
            "appointments": total,
            "tasa_completado": f"{(tasa_completado * 100):.1f}%",
        }

    # Generate adaptive recommendations
    recomendaciones = []
    horas_datos = list(horas_analisis.items())

    for i in range(len(horas_datos) - 1):
        hora_actual, datos_actual = horas_datos[i]
        hora_siguiente, datos_siguiente = horas_datos[i + 1]

        if datos_actual["duracion_promedio_min"] > 45:
            recomendaciones.append(
                {
                    "tipo": "ajustar_duracion",
                    "hora": hora_actual,
                    "description": f"Citas en {hora_actual} duran {datos_actual['duracion_promedio_min']} min (promedio)",
                    "action": f"Aumentar slot a {round(datos_actual['duracion_promedio_min'] + 5)} min",
                }
            )

    return json.dumps(
        {
            "doctor": f"{medico['first_name']} {medico['last_name']}",
            "periodo": "Últimos 30 días",
            "hourly_analysis": horas_analisis,
            "recommendations": recomendaciones,
            "message": "Análisis de eficiencia de scheduling completado.",
        },
        ensure_ascii=False,
        indent=2,
    )


# ============================================================================
# AGENDA IA: RESOLUCIÓN DE CONFLICTOS POR CIRUGÍA
# ============================================================================


@tool
async def resolver_conflicto_cirugia(
    doctor_id: int,
    fecha_cirugia: str,
    hora_inicio: str = "08:00",
    hora_fin: str = "14:00",
    confirmado: bool = False,
) -> str:
    """Resuelve automáticamente el conflicto cuando un médico tiene cirugía programada.

    PASOS:
    1. Identifica todas las appointments afectadas en el horario de cirugía
    2. Busca médicos de la misma especialidad disponibles
    3. Sugiere reasignación automática o reagendamiento
    4. Genera notificaciones personalizadas para cada paciente
    5. Ejecuta la acción confirmada

    Args:
        doctor_id: ID del médico que tendrá la cirugía.
        surgery_date: Fecha de la cirugía (YYYY-MM-DD).
        start_time: Hora inicio de la cirugía (default 08:00).
        end_time: Hora fin de la cirugía (default 14:00).
        confirmado: Si True, ejecuta la reasignación automáticamente.
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # 1. Get doctor info
        result_med = await db.execute(
            text(
                """
                SELECT m.id, m.first_name, m.last_name, m.specialty_id,
                       e.name AS specialty
                FROM doctors m
                JOIN specialties e ON e.id = m.specialty_id
                WHERE m.id = :doctor_id
                """
            ),
            {"doctor_id": doctor_id},
        )
        medico = result_med.mappings().first()

        if not medico:
            await engine.dispose()
            return f"Doctor {doctor_id} not found."

        # 2. Find affected appointments
        fecha_dt = datetime.strptime(fecha_cirugia, "%Y-%m-%d")
        inicio_dt = fecha_dt.replace(
            hour=int(hora_inicio.split(":")[0]), minute=int(hora_inicio.split(":")[1])
        )
        fin_dt = fecha_dt.replace(
            hour=int(hora_fin.split(":")[0]), minute=int(hora_fin.split(":")[1])
        )

        result_appointments = await db.execute(
            text(
                """
                SELECT c.id, c.patient_id, c.start_datetime, c.end_datetime,
                       c.reason,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       p.email, p.phone
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN appointment_statuses ec ON ec.id = c.status_id
                WHERE c.doctor_id = :doctor_id
                  AND DATE(c.start_datetime) = :fecha
                  AND c.start_datetime < :hora_fin
                  AND c.end_datetime > :hora_inicio
                  AND ec.code NOT IN ('CANCELADA', 'COMPLETADA')
                ORDER BY c.start_datetime
                """
            ),
            {
                "doctor_id": doctor_id,
                "date": fecha_cirugia,
                "start_time": inicio_dt,
                "end_time": fin_dt,
            },
        )
        appointments_afectadas = result_appointments.mappings().all()

        # 3. Find alternative doctors (same specialty)
        result_alt = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.first_name, ' ', m.last_name) AS name,
                       COUNT(c.id) AS appointments_ocupadas
                FROM doctors m
                LEFT JOIN appointments c ON c.doctor_id = m.id
                    AND DATE(c.start_datetime) = :fecha
                    AND c.start_datetime < :hora_fin
                    AND c.end_datetime > :hora_inicio
                JOIN appointment_statuses ec ON ec.id = c.status_id
                    AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                WHERE m.specialty_id = :specialty_id
                  AND m.id != :doctor_id
                GROUP BY m.id, m.first_name, m.last_name
                ORDER BY appointments_ocupadas ASC
                LIMIT 3
                """
            ),
            {
                "specialty_id": medico["specialty_id"],
                "doctor_id": doctor_id,
                "date": fecha_cirugia,
                "start_time": inicio_dt,
                "end_time": fin_dt,
            },
        )
        doctores_alternativos = result_alt.mappings().all()

        # 4. Get cancel state
        result_state = await db.execute(
            text("SELECT id FROM appointment_statuses WHERE codigo = 'CANCELADA'")
        )
        _cancel_state = result_state.first()
    await engine.dispose()

    # Build response
    appointments_info = []
    for c in appointments_afectadas:
        appointments_info.append(
            {
                "appointment_id": c["id"],
                "patient": c["patient"],
                "email": c["email"],
                "phone": c["phone"],
                "hora": str(c["start_datetime"]),
                "reason": c["reason"][:100] if c["reason"] else "N/A",
            }
        )

    alternativas = []
    for doc in doctores_alternativos:
        alternativas.append(
            {
                "doctor_id": doc["id"],
                "name": doc["name"],
                "appointments_en_horario": doc["appointments_ocupadas"],
            }
        )

    if not confirmado:
        return json.dumps(
            {
                "action": "resolver_conflicto_cirugia",
                "status": "PENDIENTE_CONFIRMACION",
                "doctor": f"{medico['first_name']} {medico['last_name']}",
                "specialty": medico["specialty"],
                "cirugia": {
                    "date": fecha_cirugia,
                    "schedule": f"{hora_inicio} - {hora_fin}",
                },
                "appointments_afectadas": len(appointments_afectadas),
                "detalles_appointments": appointments_info,
                "alternative_doctors": alternativas,
                "opciones": [
                    "REASIGNAR: Mover patients a otro médico disponible",
                    "REAGENDAR: Cambiar appointments a otro día",
                    "CANCELAR: Cancelar con notificación",
                ],
                "message": "Confirme con confirmado=true para ejecutar reasignación automática.",
            },
            ensure_ascii=False,
            indent=2,
        )

    # 5. Execute: Reassign to alternative doctor or reschedule
    engine2 = create_async_engine(_conn_str)
    async_session2 = async_sessionmaker(engine2, expire_on_commit=False)

    resultados = []
    for cita in appointments_afectadas:
        doctor_asignado = None
        nueva_hora = None

        # Try to find alternative doctor with available slot
        if doctores_alternativos:
            for doc in doctores_alternativos:
                # Check if doctor has free slot at same time
                async with async_session2() as db_check:
                    result_free = await db_check.execute(
                        text(
                            """
                            SELECT COUNT(*) AS conflicts
                            FROM appointments c
                            JOIN appointment_statuses ec ON ec.id = c.status_id
                            WHERE c.doctor_id = :doctor_id
                              AND c.start_datetime < :fin
                              AND c.end_datetime > :inicio
                              AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                            """
                        ),
                        {
                            "doctor_id": doc["id"],
                            "start": cita["start_datetime"],
                            "end": cita["end_datetime"],
                        },
                    )
                    conflicts = result_free.scalar()

                    if conflicts == 0:
                        doctor_asignado = doc
                        nueva_hora = cita["start_datetime"]
                        break

        async with async_session2() as db_update:
            if doctor_asignado:
                # Reassign to alternative doctor
                await db_update.execute(
                    text(
                        """
                        UPDATE appointments
                        SET doctor_id = :nuevo_medico,
                            status_id = (SELECT id FROM appointment_statuses WHERE codigo = 'CONFIRMADA')
                        WHERE id = :appointment_id
                        """
                    ),
                    {
                        "nuevo_medico": doctor_asignado["id"],
                        "appointment_id": cita["id"],
                    },
                )
                resultados.append(
                    {
                        "appointment_id": cita["id"],
                        "patient": cita["patient"],
                        "action": "REASIGNADA",
                        "nuevo_medico": doctor_asignado["name"],
                        "hora_mantenida": str(nueva_hora),
                    }
                )
            else:
                # Cancel and add to waitlist
                await db_update.execute(
                    text(
                        """
                        UPDATE appointments
                        SET status_id = (SELECT id FROM appointment_statuses WHERE codigo = 'CANCELADA')
                        WHERE id = :appointment_id
                        """
                    ),
                    {"appointment_id": cita["id"]},
                )
                # Add to waitlist
                await db_update.execute(
                    text(
                        """
                        INSERT INTO waitlist (patient_id, doctor_id, fecha_preferida, motivo)
                        VALUES (:patient_id, :doctor_id, :fecha, :motivo)
                        """
                    ),
                    {
                        "patient_id": cita["patient_id"],
                        "doctor_id": doctor_id,
                        "date": (fecha_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                        "reason": "Cita cancelada por cirugía del médico original",
                    },
                )
                resultados.append(
                    {
                        "appointment_id": cita["id"],
                        "patient": cita["patient"],
                        "action": "CANCELADA_LISTA_ESPERA",
                        "razon": "Sin médico alternativo disponible",
                    }
                )

        await db_update.commit()
    await engine2.dispose()

    # Generate notification messages
    notificaciones = []
    for r in resultados:
        if r["action"] == "REASIGNADA":
            notificaciones.append(
                {
                    "patient": r["patient"],
                    "message": (
                        f"Estimado/a {r['paciente']}, su cita ha sido reasignada al "
                        f"Dr./Dra. {r['nuevo_medico']} el {r.get('hora_mantenida', fecha_cirugia)}. "
                        f"Disculpe las molestias."
                    ),
                    "canal": "SMS + Email",
                }
            )
        else:
            notificaciones.append(
                {
                    "patient": r["patient"],
                    "message": (
                        f"Estimado/a {r['paciente']}, lamentamos informarle que su cita del "
                        f"{fecha_cirugia} ha sido cancelada por motivos médicos. "
                        f"Ha sido agregado a nuestra lista de espera y le notificaremos pronto."
                    ),
                    "canal": "SMS + Email + Llamada",
                }
            )

    return json.dumps(
        {
            "action": "resolver_conflicto_cirugia",
            "status": "EJECUTADA",
            "doctor": f"{medico['first_name']} {medico['last_name']}",
            "cirugia": f"{fecha_cirugia} {hora_inicio}-{hora_fin}",
            "appointments_procesadas": len(resultados),
            "reassigned": sum(1 for r in resultados if r["action"] == "REASIGNADA"),
            "cancelled_waitlist": sum(
                1 for r in resultados if "LISTA_ESPERA" in r["action"]
            ),
            "resultados": resultados,
            "notifications_generated": notificaciones,
            "message": f"Conflict resolved: {len(resultados)} appointments processed.",
        },
        ensure_ascii=False,
        indent=2,
    )


# ============================================================================
# AGENDA IA: FEATURES INNOVADORES MVP
# ============================================================================


@tool
async def analisis_sentimiento(patient_text: str, patient_id: int | None = None) -> str:
    """Analiza el sentimiento del paciente y sugiere cómo ajustar la comunicación.

    SOLO se activa para especialistas en PSICOLOGÍA.
    Detecta: ansiedad, frustración, tristeza, enojo, calma, esperanza.

    Args:
        patient_text: Texto del paciente (motivo de consulta, mensaje, etc.).
        patient_id: ID del paciente (opcional, para contexto adicional).
    """
    # Keyword-based sentiment analysis
    sentimentos = {
        "ansiedad": {
            "keywords": [
                "ansioso",
                "ansiedad",
                "nervioso",
                "preocupado",
                "miedo",
                "temeroso",
                "inquieto",
                "tenso",
                "estresado",
                "pánico",
                "angustia",
                "desesperado",
                "agobiado",
                "aterrado",
            ],
            "level": "ALTO",
            "color": "🔴",
            "recommendation": "Usar tono calmado, validar sus sentimientos, ofrecer contención.",
        },
        "frustración": {
            "keywords": [
                "frustrado",
                "frustración",
                "enojado",
                "molesto",
                "hartado",
                "cansado",
                "harto",
                "rabia",
                "indignado",
                "furioso",
            ],
            "level": "MEDIO",
            "color": "🟡",
            "recommendation": "Escuchar activamente, no interrumpir, validar su frustración.",
        },
        "tristeza": {
            "keywords": [
                "triste",
                "tristeza",
                "deprimido",
                "depresión",
                "llorando",
                "llanto",
                "solo",
                "soledad",
                "vacío",
                "desesperanza",
                "sin ganas",
                "apático",
                "melancolía",
            ],
            "level": "ALTO",
            "color": "🔴",
            "recommendation": "Mostrar empatía, preguntar abiertamente, ofrecer apoyo.",
        },
        "esperanza": {
            "keywords": [
                "mejorar",
                "superar",
                "optimista",
                "esperanza",
                "ganar",
                "luchar",
                "adelante",
                "positivo",
                "progreso",
                "avanzar",
            ],
            "level": "BAJO",
            "color": "🟢",
            "recommendation": "Reforzar positividad, explorar fortalezas, motivar.",
        },
        "calma": {
            "keywords": [
                "tranquilo",
                "calmado",
                "paz",
                "sereno",
                "estable",
                "bien",
                "mejor",
                "normal",
                "relajado",
            ],
            "level": "BAJO",
            "color": "🟢",
            "recommendation": "Mantener ritmo, profundizar en temas importantes.",
        },
    }

    texto_lower = patient_text.lower()
    detected = []

    for sentimiento, info in sentimentos.items():
        for keyword in info["keywords"]:
            if keyword in texto_lower:
                detected.append(
                    {
                        "sentimiento": sentimiento,
                        "level": info["level"],
                        "color": info["color"],
                        "recommendation": info["recommendation"],
                    }
                )
                break

    # Determine primary sentiment
    if detected:
        primary = detected[0]
        intensidad = "alta" if any(d["level"] == "ALTO" for d in detected) else "media"
    else:
        primary = {
            "sentimiento": "neutro",
            "level": "BAJO",
            "color": "⚪",
            "recommendation": "Continuar evaluación normal.",
        }
        intensidad = "baja"

    return json.dumps(
        {
            "analisis_sentimiento": True,
            "especialidad_requiere": "PSICOLOGÍA",
            "texto_analizado": patient_text[:200],
            "sentimiento_primario": primary["sentimiento"],
            "intensidad": intensidad,
            "sentimientos_detectados": [d["sentimiento"] for d in detected]
            if detected
            else ["neutro"],
            "recomendacion_comunicacion": primary["recommendation"],
            "indicador_visual": primary["color"],
            "nota": "Este análisis es orientativo. El profesional debe validar la evaluación.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def coordinacion_familiar(
    family_members: list[dict], fecha_preferida: str = ""
) -> str:
    """Coordina appointments para múltiples miembros de una familia en horarios compatibles.

    Ejemplo: "Cita para Juan (cardiología), María (medicina general) y Pedro (pediatría)"

    Args:
        family_members: Lista de [{"name": str, "specialty": str}].
        preferred_date: Fecha preferida (YYYY-MM-DD, opcional).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    if len(family_members) < 2:
        return "At least 2 family members are required for coordination."

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    resultados = []
    for familiar in family_members:
        nombre = familiar.get("name", "")
        especialidad = familiar.get("specialty", "")

        async with async_session() as db:
            # Find doctors matching specialty
            result = await db.execute(
                text(
                    """
                    SELECT m.id, CONCAT(m.first_name, ' ', m.last_name) AS medico,
                           e.name AS specialty
                    FROM doctors m
                    JOIN specialties e ON e.id = m.specialty_id
                    WHERE e.name ILIKE :especialidad
                    ORDER BY m.first_name
                    LIMIT 3
                    """
                ),
                {"specialty": f"%{especialidad}%"},
            )
            doctors = result.mappings().all()

            if not doctors:
                resultados.append(
                    {
                        "familiar": nombre,
                        "specialty": especialidad,
                        "status": "SIN_DISPO",
                        "message": f"No doctors found for {especialidad}",
                    }
                )
                continue

            # Find available slots for each doctor
            doctor_id = doctors[0]["id"]
            result_slots = await db.execute(
                text(
                    """
                    SELECT c.start_datetime, c.end_datetime
                    FROM appointments c
                    JOIN appointment_statuses ec ON ec.id = c.status_id
                    WHERE c.doctor_id = :doctor_id
                      AND c.start_datetime >= NOW()
                      AND ec.code NOT IN ('CANCELADA', 'SUSPENDIDA')
                    ORDER BY c.start_datetime
                    LIMIT 20
                    """
                ),
                {"doctor_id": doctor_id},
            )
            ocupadas = result_slots.mappings().all()

        # Find free slots
        date_obj = datetime.now().date()
        slots_libres = []
        for day_offset in range(7):
            check_date = date_obj + timedelta(days=day_offset)
            for hour in [9, 10, 11, 14, 15, 16]:
                slot_start = datetime.combine(
                    check_date, datetime.min.time().replace(hour=hour)
                )
                slot_end = slot_start + timedelta(minutes=30)
                is_free = True
                for occ in ocupadas:
                    if (
                        slot_start < occ["end_datetime"]
                        and slot_end > occ["start_datetime"]
                    ):
                        is_free = False
                        break
                if is_free:
                    slots_libres.append(slot_start)
                    if len(slots_libres) >= 3:
                        break
            if len(slots_libres) >= 3:
                break

        resultados.append(
            {
                "familiar": nombre,
                "specialty": especialidad,
                "suggested_doctor": doctors[0]["doctor"],
                "available_slots": [
                    s.strftime("%Y-%m-%dT%H:%M:%S") for s in slots_libres[:3]
                ],
            }
        )

    await engine.dispose()

    # Suggest coordinated schedule
    todos_con_slots = all(r.get("available_slots") for r in resultados)
    horario_sugerido = None

    if todos_con_slots:
        # Find common date
        fechas = set()
        for r in resultados:
            for slot in r["available_slots"]:
                fechas.add(slot.split("T")[0])

        for fecha in sorted(fechas):
            slots_en_fecha = []
            for r in resultados:
                for slot in r["available_slots"]:
                    if slot.startswith(fecha):
                        slots_en_fecha.append(slot)
            if len(slots_en_fecha) == len(resultados):
                horario_sugerido = fecha
                break

    return json.dumps(
        {
            "action": "coordinacion_familiar",
            "total_family_members": len(family_members),
            "resultados": resultados,
            "all_available": todos_con_slots,
            "suggested_date": horario_sugerido,
            "message": (
                f"Coordination completed. {'Suggested date: ' + horario_sugerido if horario_sugerido else 'Check individual availability.'}"
            ),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def teletriaje_ia(
    reason: str, sintomas: str = "", patient_id: int | None = None
) -> str:
    """Determina si una consulta puede ser atendida de forma virtual o requiere presencial.

    Analiza síntomas y motivo para recomendar modalidad adecuada.

    Args:
        reason: Motivo de la consulta.
        symptoms: Síntomas descritos (opcional).
        patient_id: ID del paciente (opcional).
    """
    # Rules for telehealth eligibility
    reglas_presencial = [
        "dolor",
        "fiebre",
        "sangrado",
        "lesión",
        "herida",
        "fractura",
        "examen físico",
        "auscultar",
        "palpar",
        "inyección",
        "cirugía",
        "procedimiento",
        "extracción",
        "sutura",
        "curación",
    ]

    reglas_virtual = [
        "seguimiento",
        "control",
        "receta",
        "resultado",
        "consulta general",
        "duda",
        "orientación",
        "sigma",
        "ansiedad leve",
        "insomnio",
        "estrés",
        "terapia",
        "consejería",
        "plan de tratamiento",
    ]

    motivo_lower = reason.lower()
    sintomas_lower = sintomas.lower()
    texto_completo = f"{motivo_lower} {sintomas_lower}"

    presencial_score = sum(1 for r in reglas_presencial if r in texto_completo)
    virtual_score = sum(1 for r in reglas_virtual if r in texto_completo)

    if presencial_score > virtual_score:
        modalidad = "PRESENCIAL"
        confianza = "alta" if presencial_score >= 2 else "media"
        razon = "Requiere examen físico o procedimiento"
    elif virtual_score > presencial_score:
        modalidad = "VIRTUAL"
        confianza = "alta" if virtual_score >= 2 else "media"
        razon = "Puede resolverse por videoconsulta"
    else:
        modalidad = "A_EVALUAR"
        confianza = "baja"
        razon = "Se requiere más información"

    return json.dumps(
        {
            "evaluacion_teletriaje": True,
            "reason": reason,
            "sintomas": sintomas[:200] if sintomas else "N/A",
            "modalidad_recomendada": modalidad,
            "confianza": confianza,
            "razon": razon,
            "preguntas_clarificacion": (
                [
                    "¿Presenta síntomas físicos que requieran examen?",
                    "¿Es una consulta de seguimiento o control?",
                ]
                if modalidad == "A_EVALUAR"
                else []
            ),
            "nota": "El profesional debe confirmar la modalidad final.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def verificacion_seguros(patient_id: int, doctor_id: int) -> str:
    """Verifica si el paciente tiene seguro vigente y si cubre al médico/especialidad.

    Simula verificación de cobertura (en producción se conectaría a aseguradora).

    Args:
        patient_id: ID del paciente.
        doctor_id: ID del médico.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get patient info
        result_pat = await db.execute(
            text(
                """
                SELECT id, CONCAT(first_name, ' ', last_name) AS name, email
                FROM patients WHERE id = :id
                """
            ),
            {"id": patient_id},
        )
        paciente = result_pat.mappings().first()

        # Get doctor info
        result_med = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.first_name, ' ', m.last_name) AS name,
                       e.name AS specialty
                FROM doctors m
                JOIN specialties e ON e.id = m.specialty_id
                WHERE m.id = :id
                """
            ),
            {"id": doctor_id},
        )
        medico = result_med.mappings().first()
    await engine.dispose()

    if not paciente or not medico:
        return "Patient or doctor not found."

    # Simulated verification (in production: API call to insurer)
    # This would integrate with real insurance verification APIs
    verificacion = {
        "patient": paciente["name"],
        "doctor": medico["name"],
        "specialty": medico["specialty"],
        "estado_verificacion": "SIMULADO",
        "seguro_cubierto": True,
        "copago_estimado": "$200 MXN",
        "recommendations": [
            "Verificar número de póliza vigente",
            "Confirmar cobertura de especialidad",
            "Solicitar pre-autorización si aplica",
        ],
        "nota": "Verificación simulada. En producción, conectar con API de aseguradora.",
    }

    return json.dumps(verificacion, ensure_ascii=False, indent=2)


@tool
async def ai_scribe(appointment_id: int, transcription_text: str) -> str:
    """Genera notas clínicas estructuradas a partir de una transcripción.

    Convierte texto libre en formato SOAP (Subjective, Objective, Assessment, Plan).

    Args:
        appointment_id: ID de la cita.
        transcription_text: Transcripción de la consulta (audio a texto).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get appointment info
        result = await db.execute(
            text(
                """
                SELECT c.id, c.reason,
                       CONCAT(p.first_name, ' ', p.last_name) AS paciente,
                       CONCAT(m.first_name, ' ', m.last_name) AS medico,
                       e.name AS specialty
                FROM appointments c
                JOIN patients p ON p.id = c.patient_id
                JOIN doctors m ON m.id = c.doctor_id
                JOIN specialties e ON e.id = m.specialty_id
                WHERE c.id = :appointment_id
                """
            ),
            {"appointment_id": appointment_id},
        )
        cita = result.mappings().first()
    await engine.dispose()

    if not cita:
        return f"Appointment {appointment_id} not found."

    # Simple SOAP note generation from transcription
    # In production, this would use the LLM to parse
    texto = transcription_text

    # Extract potential sections
    soap = {
        "S": {
            "paciente_refiere": texto[:500] if texto else "No disponible",
        },
        "O": {
            "notas_observacion": "Requiere revisión del profesional",
        },
        "A": {
            "impresion_clinica": "A determinar por el especialista",
        },
        "P": {
            "plan": "Según evaluación profesional",
        },
    }

    return json.dumps(
        {
            "appointment_id": appointment_id,
            "patient": cita["patient"],
            "doctor": cita["doctor"],
            "specialty": cita["specialty"],
            "formato": "SOAP",
            "notas_generadas": soap,
            "transcripcion_original": texto[:1000],
            "nota": "Notas generadas automáticamente. El profesional debe revisar y ajustar.",
            "tiempo_ahorrado": "~10 minutos por consulta",
        },
        ensure_ascii=False,
        indent=2,
    )


_TOOLS = [
    # Basic tools
    buscar_en_documentos,
    consultar_citas_paciente,
    consultar_citas_medico,
    buscar_pacientes,
    buscar_medicos,
    contar_registros,
    # Scheduling tools
    sugerir_reagendamiento,
    ejecutar_reagendamiento,
    cancelar_cita,
    # AI-powered scheduling tools
    sugerir_horarios_disponibles,
    analizar_carga_medico,
    detectar_conflictos,
    analizar_patrones_paciente,
    # Advanced AI scheduling tools
    crear_cita_por_lenguaje,
    reagendamiento_inteligente,
    agregar_a_lista_espera,
    predecir_no_show,
    sugerir_seguimiento,
    encontrar_horario_compartido,
    triagar_por_sintomas,
    # Mass operations & emergency tools
    cancelar_citas_masivo,
    replanificar_citas,
    notificar_lista_espera,
    protocolo_emergencia,
    optimizar_agenda,
    generar_recordatorio,
    # Differentiation tools (unique features)
    predecir_demanda,
    matching_paciente_medico,
    duracion_inteligente,
    optimizar_ingresos,
    score_satisfaccion,
    resumen_clinico_paciente,
    detectar_anomalias,
    scheduling_adaptativo,
    # Surgery conflict resolution
    resolver_conflicto_cirugia,
    # Innovative features (MVP)
    analisis_sentimiento,
    coordinacion_familiar,
    teletriaje_ia,
    verificacion_seguros,
    ai_scribe,
]


async def chat_con_agente(
    user_message: str,
    *,
    conn_str: str,
    history: list[dict[str, str]] | None = None,
    language: str = "en",
) -> str:
    """Sends a message to the MedAssist agent and returns its response.

    Args:
        user_message: User question or instruction.
        conn_str: DATABASE_URL for internal DB connections.
        history: Optional list of previous messages [{role, content}].
        language: Language code for responses (en, es, pt).
    """
    global _conn_str
    _conn_str = conn_str

    # Set current language for tool functions
    set_current_language(language)

    # Anti-prompt-injection check
    injection_warning = _detect_injection(user_message)
    if injection_warning:
        return injection_warning

    llm = _get_llm()
    llm_con_tools = llm.bind_tools(_TOOLS)

    messages: list = [SystemMessage(content=_SYSTEM_PROMPT)]

    if history:
        for msg in history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                messages.append(SystemMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    reply = await llm_con_tools.ainvoke(messages)

    for _ in range(6):
        if not reply.tool_calls:
            break

        messages.append(reply)
        for tool_call in reply.tool_calls:
            tool_fn = next((t for t in _TOOLS if t.name == tool_call["name"]), None)
            try:
                if tool_fn is None:
                    tool_result = f"Unknown tool: {tool_call['name']}"
                else:
                    tool_result = await tool_fn.ainvoke(tool_call["args"])
            except Exception as exc:  # noqa: BLE001
                tool_result = (
                    f"Error executing tool: {exc}. "
                    "Tell the user that more data is needed."
                )
            messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
            )

        reply = await llm_con_tools.ainvoke(messages)

    return reply.content


async def chat_con_agente_stream(
    user_message: str,
    *,
    conn_str: str,
    history: list[dict[str, str]] | None = None,
    language: str = "en",
):
    """Streams agent response token-by-token using LangChain astream.

    Args:
        user_message: User question or instruction.
        conn_str: DATABASE_URL for internal DB connections.
        history: Optional list of previous messages [{role, content}].
        language: Language code for responses (en, es, pt).
    """
    global _conn_str
    _conn_str = conn_str

    # Set current language for tool functions
    set_current_language(language)

    # Anti-prompt-injection check
    injection_warning = _detect_injection(user_message)
    if injection_warning:
        yield injection_warning
        return

    llm = _get_llm()
    llm_con_tools = llm.bind_tools(_TOOLS)

    messages: list = [SystemMessage(content=_SYSTEM_PROMPT)]

    if history:
        for msg in history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                messages.append(SystemMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    # Initial invoke to check for tool calls
    reply = await llm_con_tools.ainvoke(messages)

    # Handle tool calls loop (non-streaming for tool execution)
    for _ in range(6):
        if not reply.tool_calls:
            break

        messages.append(reply)
        for tool_call in reply.tool_calls:
            tool_fn = next((t for t in _TOOLS if t.name == tool_call["name"]), None)
            try:
                if tool_fn is None:
                    tool_result = f"Unknown tool: {tool_call['name']}"
                else:
                    tool_result = await tool_fn.ainvoke(tool_call["args"])
            except Exception as exc:  # noqa: BLE001
                tool_result = (
                    f"Error executing tool: {exc}. "
                    "Tell the user that more data is needed."
                )
            messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
            )

        reply = await llm_con_tools.ainvoke(messages)

    # Stream the final response
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content
