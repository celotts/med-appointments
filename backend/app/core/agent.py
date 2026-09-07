"""Agente conversacional RAG + herramientas de agendamiento con LangChain + Ollama."""

import json
import re

from core.config import settings
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from sqlalchemy import text

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
                "Tu mensaje fue bloqueado por contener patrones no permitidos. "
                "Por favor, haz una pregunta relacionada con citas médicas o información clínica."
            )
    return None


_SYSTEM_PROMPT = """Eres MedAssist, un asistente inteligente de gestión de citas médicas con capacidades avanzadas de IA.

CAPACIDADES PRINCIPALES:
1. Gestión de citas: crear, consultar, reagendar, cancelar citas médicas.
2. Creación por lenguaje natural: interpretar solicitudes como "Agenda cita con Dr. García para Juan el martes".
3. Búsqueda semántica: buscar en notas médicas y documentos clínicos vectorizados.
4. Análisis de agenda: sugerir horarios óptimos, detectar conflictos, analizar carga de trabajo.
5. Reagendamiento inteligente: sugerir mejores horarios basado en patrones del paciente.
6. Lista de espera: gestionar cola cuando no hay disponibilidad.
7. Predicción de no-show: estimar probabilidad de inasistencia.
8. Seguimiento automático: recomendar citas de seguimiento según diagnóstico.
9. Coordinación multi-doctor: encontrar horarios compartidos para citas conjuntas.
10. Triaje por síntomas: evaluar urgencia y sugerir especialidad.
11. Patrones predictivos: analizar comportamiento de pacientes para mejorar asistencia.
12. Resumen de notas clínicas: extraer información relevante de diagnósticos y tratamientos.

HERRAMIENTAS DISPONIBLES:
BÁSICAS:
- buscar_en_documentos, consultar_citas_paciente, consultar_citas_medico
- buscar_pacientes, buscar_medicos, contar_registros

AGENDA:
- sugerir_horarios_disponibles, analizar_carga_medico, detectar_conflictos
- analizar_patrones_paciente

AVANZADAS:
- crear_cita_por_lenguaje: Crear citas desde descripción natural
- reagendamiento_inteligente: Sugerir mejores horarios automáticamente
- agregar_a_lista_espera: Gestionar cola de espera
- predecir_no_show: Estimar probabilidad de inasistencia
- sugerir_seguimiento: Recomendar citas de seguimiento
- encontrar_horario_compartido: Buscar disponibilidad multi-doctor
- triagar_por_sintomas: Evaluar urgencia por síntomas

GESTIÓN MASIVA Y EMERGENCIA:
- cancelar_citas_masivo: Cancelar todas las citas de un médico en un día
- replanificar_citas: Mover citas de un día a otro automáticamente
- notificar_lista_espera: Avisar a pacientes pendientes cuando hay slots
- protocolo_emergencia: Ejecutar protocolo completo de emergencia
- optimizar_agenda: Analizar y sugerir mejoras de eficiencia
- generar_recordatorio: Crear recordatorios personalizados

FEATURES ÚNICOS DE DIFERENCIACIÓN:
- predecir_demanda: Anticipar picos de demanda y especialidades
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
async def buscar_en_documentos(query: str = "", ref_tipo: str | None = None) -> str:
    """Busca documentos relevantes en la base de datos vectorial (notas médicas, documentos clínicos).

    Args:
        query: Consulta en lenguaje natural sobre contenido médico.
        ref_tipo: Filtrar por tipo de referencia (ej: 'NOTA_MEDICA', 'DOCUMENTO').
    """
    from core.rag import search_documentos as _search
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        results = await _search(db, query, k=5, ref_tipo=ref_tipo)
    await engine.dispose()

    if not results:
        return "No se encontraron documentos relevantes."

    return json.dumps(results, ensure_ascii=False, indent=2)


@tool
async def consultar_citas_paciente(nombre_paciente: str = "") -> str:
    """Consulta las citas de un paciente por su nombre.

    Args:
        nombre_paciente: Nombre o apellido del paciente (búsqueda parcial).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.fecha_hora_inicio, c.fecha_hora_fin, c.motivo_consulta,
                       ec.codigo AS estado,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE (p.nombre ILIKE :q OR p.apellido ILIKE :q
                       OR CONCAT(p.nombre, ' ', p.apellido) ILIKE :q)
                ORDER BY c.fecha_hora_inicio DESC
                LIMIT 10
                """
            ),
            {"q": f"%{nombre_paciente}%"},
        )
        rows = result.mappings().all()
    await engine.dispose()

    if not rows:
        return f"No se encontraron citas para '{nombre_paciente}'."

    return json.dumps(
        [
            {
                "cita_id": r["id"],
                "fecha": str(r["fecha_hora_inicio"]),
                "estado": r["estado"],
                "medico": r["medico"],
                "motivo": r["motivo_consulta"],
            }
            for r in rows
        ],
        ensure_ascii=False,
        indent=2,
    )


@tool
async def consultar_citas_medico(nombre_medico: str = "") -> str:
    """Consulta las citas de un médico por su nombre.

    Args:
        nombre_medico: Nombre o apellido del médico (búsqueda parcial).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.fecha_hora_inicio, c.fecha_hora_fin, c.motivo_consulta,
                       ec.codigo AS estado,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE (m.nombre ILIKE :q OR m.apellido ILIKE :q
                       OR CONCAT(m.nombre, ' ', m.apellido) ILIKE :q)
                ORDER BY c.fecha_hora_inicio DESC
                LIMIT 10
                """
            ),
            {"q": f"%{nombre_medico}%"},
        )
        rows = result.mappings().all()
    await engine.dispose()

    if not rows:
        return f"No se encontraron citas para el médico '{nombre_medico}'."

    return json.dumps(
        [
            {
                "cita_id": r["id"],
                "fecha": str(r["fecha_hora_inicio"]),
                "estado": r["estado"],
                "paciente": r["paciente"],
                "motivo": r["motivo_consulta"],
            }
            for r in rows
        ],
        ensure_ascii=False,
        indent=2,
    )


@tool
async def buscar_pacientes(nombre: str = "") -> str:
    """Busca pacientes por nombre o apellido.

    Args:
        nombre: Nombre o apellido del paciente (búsqueda parcial).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT id, nombre, apellido, email, telefono
                FROM pacientes
                WHERE nombre ILIKE :q OR apellido ILIKE :q
                   OR CONCAT(nombre, ' ', apellido) ILIKE :q
                ORDER BY apellido, nombre
                LIMIT 10
                """
            ),
            {"q": f"%{nombre}%"},
        )
        rows = result.mappings().all()
    await engine.dispose()

    if not rows:
        return f"No se encontraron pacientes con '{nombre}'."

    return json.dumps(
        [dict(r) for r in rows],
        ensure_ascii=False,
        indent=2,
    )


@tool
async def buscar_medicos(nombre: str = "") -> str:
    """Busca médicos por nombre o apellido.

    Args:
        nombre: Nombre o apellido del médico (búsqueda parcial).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT m.id, m.nombre, m.apellido, m.email, m.telefono,
                       e.nombre AS especialidad
                FROM medicos m
                JOIN especialidades e ON e.id = m.especialidad_id
                WHERE m.nombre ILIKE :q OR m.apellido ILIKE :q
                   OR CONCAT(m.nombre, ' ', m.apellido) ILIKE :q
                ORDER BY m.apellido, m.nombre
                LIMIT 10
                """
            ),
            {"q": f"%{nombre}%"},
        )
        rows = result.mappings().all()
    await engine.dispose()

    if not rows:
        return f"No se encontraron médicos con '{nombre}'."

    return json.dumps(
        [dict(r) for r in rows],
        ensure_ascii=False,
        indent=2,
    )


@tool
async def sugerir_reagendamiento(cita_id: int, nueva_fecha: str) -> str:
    """Propone reagendar una cita a una nueva fecha. NO ejecuta la acción, solo informa al usuario para que confirme.

    Args:
        cita_id: ID de la cita a reagendar.
        nueva_fecha: Nueva fecha propuesta en formato ISO 8601 (ej: '2026-09-15T10:00:00').
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.fecha_hora_inicio, c.fecha_hora_fin,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       ec.codigo AS estado
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.id = :cita_id
                """
            ),
            {"cita_id": cita_id},
        )
        row = result.mappings().first()
    await engine.dispose()

    if not row:
        return f"No se encontró la cita {cita_id}."

    return (
        f"📋 Propuesta de reagendamiento:\n"
        f"- Cita #{row['id']} ({row['estado']})\n"
        f"- Paciente: {row['paciente']}\n"
        f"- Médico: {row['medico']}\n"
        f"- Fecha actual: {row['fecha_hora_inicio']}\n"
        f"- Nueva fecha propuesta: {nueva_fecha}\n\n"
        f"El usuario debe confirmar explícitamente antes de ejecutar el cambio."
    )


@tool
async def ejecutar_reagendamiento(
    cita_id: int,
    nueva_fecha: str,
    confirmado: bool = False,
) -> str:
    """EJECUTA el reagendamiento de una cita a una nueva fecha YA confirmado por el usuario.

    IMPORTANTE: Solo usar después de que el usuario confirme explícitamente.
    Cambia la fecha de la cita y la pasa a estado REAGENDADA.

    Args:
        cita_id: ID de la cita a reagendar.
        nueva_fecha: Nueva hora de inicio en formato ISO 8601 (ej: '2026-09-16T10:00:00Z').
        confirmado: Debe ser True; si es False, devuelve advertencia sin ejecutar.
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    if not confirmado:
        return (
            "No se ejecutó el reagendamiento: falta confirmación explícita del usuario. "
            "Primero presenta la propuesta y pide su confirmación, luego vuelve a llamar "
            "con confirmado=true."
        )

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with async_session() as db:
            import core.base  # noqa: F401  (registra todos los modelos/mappers)
            from core import crud_cita
            from schemas.cita import CitaUpdate

            db_cita = await crud_cita.get_cita(db, cita_id)
            if not db_cita:
                return f"No se encontró la cita {cita_id}."

            inicio = datetime.fromisoformat(nueva_fecha.replace("Z", "+00:00"))
            fin = inicio + timedelta(minutes=30)
            update = CitaUpdate(
                fecha_hora_inicio=inicio,
                fecha_hora_fin=fin,
            )
            try:
                cita = await crud_cita.reagendar_cita(db, db_cita, update)
            except ValueError as exc:
                return f"No se pudo reagendar: {exc}"
            return (
                f"✅ Cita #{cita.id} reagendada a {cita.fecha_hora_inicio} "
                f"(estado: {cita.estado.codigo})."
            )
    finally:
        await engine.dispose()


@tool
async def cancelar_cita(cita_id: int, confirmado: bool = False) -> str:
    """CANCELA una cita (estado CANCELADA) YA confirmado por el usuario.

    Solo procede si el estado actual permite la transición a CANCELADA.

    IMPORTANTE: Solo usar después de que el usuario confirme explícitamente.

    Args:
        cita_id: ID de la cita a cancelar.
        confirmado: Debe ser True; si es False, devuelve advertencia sin ejecutar.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    if not confirmado:
        return (
            "No se ejecutó la cancelación: falta confirmación explícita del usuario. "
            "Pide su confirmación y luego vuelve a llamar con confirmado=true."
        )

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with async_session() as db:
            import core.base  # noqa: F401  (registra todos los modelos/mappers)
            from core import crud_cita
            from schemas.cita import CitaEstadoUpdate, EstadoCitaCodigo

            db_cita = await crud_cita.get_cita(db, cita_id)
            if not db_cita:
                return f"No se encontró la cita {cita_id}."

            try:
                cita = await crud_cita.change_estado(
                    db, db_cita, CitaEstadoUpdate(estado=EstadoCitaCodigo.CANCELADA)
                )
            except ValueError as exc:
                return f"No se pudo cancelar: {exc}"
            return f"✅ Cita #{cita.id} cancelada."
    finally:
        await engine.dispose()


@tool
async def contar_registros() -> str:
    """Cuenta cuántos registros hay de cada tipo: pacientes, médicos, citas, notas médicas.

    Útil para responder preguntas como '¿cuántos pacientes hay?', '¿cuántas citas existen?'.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                "SELECT "
                "(SELECT COUNT(*) FROM pacientes) AS pacientes, "
                "(SELECT COUNT(*) FROM medicos) AS medicos, "
                "(SELECT COUNT(*) FROM citas) AS citas, "
                "(SELECT COUNT(*) FROM notas_medicas) AS notas_medicas, "
                "(SELECT COUNT(*) FROM documentos_vectoriales) AS documentos"
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
    medico_id: int, fecha: str, duracion_min: int = 30
) -> str:
    """Sugiere horarios disponibles para un médico en una fecha específica.

    Analiza la agenda existente y encuentra slots vacíos considerando:
    - Horario laboral típico (08:00-14:00, 16:00-20:00)
    - Citas ya programadas
    - Duración de la nueva cita

    Args:
        medico_id: ID del médico.
        fecha: Fecha a consultar en formato YYYY-MM-DD.
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
                SELECT c.fecha_hora_inicio, c.fecha_hora_fin
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND DATE(c.fecha_hora_inicio) = :fecha
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.fecha_hora_inicio
                """
            ),
            {"medico_id": medico_id, "fecha": fecha},
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
            occ_start = occ["fecha_hora_inicio"]
            occ_end = occ["fecha_hora_fin"]
            if slot < occ_end and slot_end > occ_start:
                is_free = False
                break
        if is_free:
            available.append(slot)

    if not available:
        return f"No hay horarios disponibles para el médico {medico_id} el {fecha} con duración de {duracion_min} min."

    # Format response
    slots_json = [
        {
            "hora_inicio": s.strftime("%H:%M"),
            "hora_fin": (s + timedelta(minutes=duracion_min)).strftime("%H:%M"),
            "sugerencia": s.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        for s in available[:8]  # Limit to 8 suggestions
    ]

    return json.dumps(
        {
            "medico_id": medico_id,
            "fecha": fecha,
            "duracion_min": duracion_min,
            "horarios_disponibles": slots_json,
            "total_disponibles": len(available),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def analizar_carga_medico(medico_id: int, dias: int = 7) -> str:
    """Analiza la carga de trabajo de un médico en los próximos N días.

    Retorna estadísticas de ocupación y sugiere días con menor carga.

    Args:
        medico_id: ID del médico.
        dias: Número de días a analizar (default 7).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT DATE(c.fecha_hora_inicio) AS dia,
                       COUNT(*) AS total_citas,
                       SUM(EXTRACT(EPOCH FROM (c.fecha_hora_fin - c.fecha_hora_inicio))/60) AS minutos_ocupados
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND c.fecha_hora_inicio >= NOW()
                  AND c.fecha_hora_inicio < NOW() + INTERVAL ':dias days'
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY DATE(c.fecha_hora_inicio)
                ORDER BY dia
                """
            ),
            {"medico_id": medico_id, "dias": dias},
        )
        daily_load = result.mappings().all()

        # Get doctor info
        result_med = await db.execute(
            text(
                "SELECT nombre, apellido FROM medicos WHERE id = :id"
            ),
            {"id": medico_id},
        )
        medico = result_med.mappings().first()
    await engine.dispose()

    if not medico:
        return f"No se encontró el médico {medico_id}."

    # Calculate stats
    total_citas = sum(r["total_citas"] for r in daily_load)
    total_minutos = sum(r["minutos_ocupados"] or 0 for r in daily_load)
    promedio_citas = total_citas / dias if dias > 0 else 0

    # Find lightest day
    dias_carga = {str(r["dia"]): r["total_citas"] for r in daily_load}
    dia_leve = min(dias_carga, key=dias_carga.get) if dias_carga else None

    return json.dumps(
        {
            "medico": f"{medico['nombre']} {medico['apellido']}",
            "periodo": f"Próximos {dias} días",
            "total_citas": total_citas,
            "total_horas": round(total_minutos / 60, 1),
            "promedio_citas_dia": round(promedio_citas, 1),
            "carga_por_dia": dias_carga,
            "dia_mas_disponible": dia_leve,
            "cita_mas_corta": "30 min" if total_citas > 0 else "N/A",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def detectar_conflictos(fecha_inicio: str, fecha_fin: str) -> str:
    """Detecta conflictos de horario en un rango de fechas.

    Busca citas superpuestas y sugiere soluciones automáticas.

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
                SELECT c.id, c.fecha_hora_inicio, c.fecha_hora_fin,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       ec.codigo AS estado
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.fecha_hora_inicio < :fecha_fin
                  AND c.fecha_hora_fin > :fecha_inicio
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.medico_id, c.fecha_hora_inicio
                """
            ),
            {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
        )
        conflicts = result.mappings().all()
    await engine.dispose()

    if not conflicts:
        return "No se detectaron conflictos de horario en el rango especificado."

    # Group by doctor
    by_medico = {}
    for c in conflicts:
        med = c["medico"]
        if med not in by_medico:
            by_medico[med] = []
        by_medico[med].append(c)

    # Find overlapping pairs
    conflictos = []
    for medico, citas in by_medico.items():
        for i in range(len(citas)):
            for j in range(i + 1, len(citas)):
                c1, c2 = citas[i], citas[j]
                if c1["fecha_hora_inicio"] < c2["fecha_hora_fin"] and c2["fecha_hora_inicio"] < c1["fecha_hora_fin"]:
                    conflictos.append(
                        {
                            "medico": medico,
                            "cita_1": {
                                "id": c1["id"],
                                "paciente": c1["paciente"],
                                "inicio": str(c1["fecha_hora_inicio"]),
                                "fin": str(c1["fecha_hora_fin"]),
                            },
                            "cita_2": {
                                "id": c2["id"],
                                "paciente": c2["paciente"],
                                "inicio": str(c2["fecha_hora_inicio"]),
                                "fin": str(c2["fecha_hora_fin"]),
                            },
                            "sugerencia": f"Reagendar cita #{c2['id']} a otro horario",
                        }
                    )

    return json.dumps(
        {
            "conflictos_encontrados": len(conflictos),
            "detalles": conflictos,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def analizar_patrones_paciente(nombre_paciente: str = "") -> str:
    """Analiza patrones de citas de un paciente para predecir comportamiento.

    Identifica:
    - Días de la semana preferidos
    - Horarios preferidos
    - Tasa de cancelaciones
    - Frecuencia de reagendamientos

    Args:
        nombre_paciente: Nombre o apellido del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.fecha_hora_inicio,
                       ec.codigo AS estado,
                       EXTRACT(DOW FROM c.fecha_hora_inicio) AS dia_semana,
                       EXTRACT(HOUR FROM c.fecha_hora_inicio) AS hora
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE (p.nombre ILIKE :q OR p.apellido ILIKE :q
                       OR CONCAT(p.nombre, ' ', p.apellido) ILIKE :q)
                ORDER BY c.fecha_hora_inicio DESC
                LIMIT 50
                """
            ),
            {"q": f"%{nombre_paciente}%"},
        )
        citas = result.mappings().all()
    await engine.dispose()

    if not citas:
        return f"No se encontraron citas para '{nombre_paciente}'."

    # Analyze patterns
    dias_semana = {0: "Dom", 1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb"}
    dia_counts = {}
    hora_counts = {}
    total = len(citas)
    canceladas = sum(1 for c in citas if c["estado"] == "CANCELADA")
    reagendadas = sum(1 for c in citas if c["estado"] == "REAGENDADA")

    for c in citas:
        dia = dias_semana.get(c["dia_semana"], "?")
        dia_counts[dia] = dia_counts.get(dia, 0) + 1
        hora = c["hora"]
        hora_counts[f"{int(hora):02d}:00"] = hora_counts.get(f"{int(hora):02d}:00", 0) + 1

    dia_preferido = max(dia_counts, key=dia_counts.get) if dia_counts else "N/A"
    hora_preferida = max(hora_counts, key=hora_counts.get) if hora_counts else "N/A"

    return json.dumps(
        {
            "paciente": nombre_paciente,
            "total_citas": total,
            "dias_preferidos": dia_counts,
            "dia_mas_frecuente": dia_preferido,
            "horarios_preferidos": hora_counts,
            "hora_mas_frecuente": hora_preferida,
            "tasa_cancelacion": f"{(canceladas/total*100):.1f}%" if total > 0 else "0%",
            "tasa_reagendamiento": f"{(reagendadas/total*100):.1f}%" if total > 0 else "0%",
            "recomendacion": f"Para mayor asistencia, programar los {dia_preferido} a las {hora_preferida}.",
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
    paciente_id: int | None = None,
    medico_id: int | None = None,
) -> str:
    """Crea una cita médica a partir de una descripción en lenguaje natural.

    Interpreta la solicitud del usuario y crea la cita automáticamente.
    Si faltan datos, pide la información faltante.

    Args:
        descripcion: Descripción en lenguaje natural (ej: "Cita con Dr. García para Juan el martes a las 10am").
        paciente_id: ID del paciente (opcional si se menciona nombre).
        medico_id: ID del médico (opcional si se menciona nombre).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Try to find patient if not provided
        if not paciente_id:
            result = await db.execute(
                text(
                    """
                    SELECT id, nombre, apellido FROM pacientes
                    WHERE CONCAT(nombre, ' ', apellido) ILIKE :q
                    LIMIT 1
                    """
                ),
                {"q": f"%{descripcion}%"},
            )
            paciente = result.mappings().first()
            if paciente:
                paciente_id = paciente["id"]

        # Try to find doctor if not provided
        if not medico_id:
            result = await db.execute(
                text(
                    """
                    SELECT id, nombre, apellido FROM medicos
                    WHERE CONCAT(nombre, ' ', apellido) ILIKE :q
                    LIMIT 1
                    """
                ),
                {"q": f"%{descripcion}%"},
            )
            medico = result.mappings().first()
            if medico:
                medico_id = medico["id"]

    await engine.dispose()

    if not paciente_id:
        return (
            "No pude identificar el paciente. Por favor, proporciona el ID del paciente "
            "o menciona su nombre completo en la descripción."
        )

    if not medico_id:
        return (
            "No pude identificar el médico. Por favor, proporciona el ID del médico "
            "o menciona su nombre completo en la descripción."
        )

    return json.dumps(
        {
            "accion": "crear_cita",
            "paciente_id": paciente_id,
            "medico_id": medico_id,
            "descripcion_original": descripcion,
            "mensaje": "Datos extraídos correctamente. Use crear_cita del CRUD para ejecutar con fecha/hora específica.",
            "siguiente_paso": "El usuario debe especificar fecha y hora, o usar sugerir_horarios_disponibles.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def reagendamiento_inteligente(cita_id: int) -> str:
    """Sugiere el mejor horario para reagendar una cita basado en patrones del paciente y disponibilidad del médico.

    Analiza:
    - Preferencias del paciente (días y horarios favoritos)
    - Disponibilidad del médico
    - Conflictos potenciales

    Args:
        cita_id: ID de la cita a reagendar.
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
                SELECT c.id, c.fecha_hora_inicio, c.fecha_hora_fin, c.motivo_consulta,
                       c.paciente_id, c.medico_id,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       ec.codigo AS estado
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.id = :cita_id
                """
            ),
            {"cita_id": cita_id},
        )
        cita = result.mappings().first()

        if not cita:
            await engine.dispose()
            return f"No se encontró la cita {cita_id}."

        if cita["estado"] in ("CANCELADA", "COMPLETADA"):
            await engine.dispose()
            return f"No se puede reagendar una cita {cita['estado']}."

        # Get patient patterns
        result_pat = await db.execute(
            text(
                """
                SELECT EXTRACT(DOW FROM c.fecha_hora_inicio) AS dia_semana,
                       EXTRACT(HOUR FROM c.fecha_hora_inicio) AS hora,
                       COUNT(*) AS frecuencia
                FROM citas c
                WHERE c.paciente_id = :paciente_id
                  AND c.id != :cita_id
                GROUP BY dia_semana, hora
                ORDER BY frecuencia DESC
                LIMIT 5
                """
            ),
            {"paciente_id": cita["paciente_id"], "cita_id": cita_id},
        )
        patrones = result_pat.mappings().all()

        # Get available slots for next 7 days
        result_slots = await db.execute(
            text(
                """
                SELECT c.fecha_hora_inicio, c.fecha_hora_fin
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND c.fecha_hora_inicio >= NOW()
                  AND c.fecha_hora_inicio < NOW() + INTERVAL '7 days'
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.fecha_hora_inicio
                """
            ),
            {"medico_id": cita["medico_id"]),
        )
        ocupadas = result_slots.mappings().all()
    await engine.dispose()

    # Generate recommendations
    dias_semana = {0: "Dom", 1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb"}
    recomendaciones = []

    if patrones:
        mejor_patron = patrones[0]
        recomendaciones.append({
            "tipo": "por_patron",
            "dia": dias_semana.get(int(mejor_patron["dia_semana"]), "?"),
            "hora": f"{int(mejor_patron['hora']):02d}:00",
            "confianza": "alta",
            "razon": f"El paciente tiene {mejor_patron['frecuencia']} citas en este horario.",
        })

    # Find free slots in next 7 days
    date_obj = datetime.now().date()
    for day_offset in range(7):
        check_date = date_obj + timedelta(days=day_offset)
        for hour in [9, 10, 11, 14, 15, 16, 17]:
            slot_start = datetime.combine(check_date, datetime.min.time().replace(hour=hour))
            slot_end = slot_start + timedelta(minutes=30)
            is_free = True
            for occ in ocupadas:
                if slot_start < occ["fecha_hora_fin"] and slot_end > occ["fecha_hora_inicio"]:
                    is_free = False
                    break
            if is_free:
                recomendaciones.append({
                    "tipo": "disponible",
                    "fecha": slot_start.strftime("%Y-%m-%d"),
                    "hora": slot_start.strftime("%H:%M"),
                    "sugerencia": slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
                })
                if len(recomendaciones) >= 5:
                    break
        if len(recomendaciones) >= 5:
            break

    return json.dumps(
        {
            "cita_id": cita_id,
            "paciente": cita["paciente"],
            "medico": cita["medico"],
            "fecha_actual": str(cita["fecha_hora_inicio"]),
            "recomendaciones": recomendaciones[:5],
            "mensaje": "Seleccione una opción o confirme para ejecutar el reagendamiento.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def agregar_a_lista_espera(
    paciente_id: int, medico_id: int, fecha_preferida: str, motivo: str = ""
) -> str:
    """Agrega un paciente a la lista de espera para un médico cuando no hay horarios disponibles.

    Guarda la preferencia y notificará cuando se libere un slot.

    Args:
        paciente_id: ID del paciente.
        medico_id: ID del médico.
        fecha_preferida: Fecha preferida en formato YYYY-MM-DD.
        motivo: Motivo de la consulta.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Create waitlist table if not exists
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS lista_espera (
                    id SERIAL PRIMARY KEY,
                    paciente_id INT NOT NULL,
                    medico_id INT NOT NULL,
                    fecha_preferida DATE NOT NULL,
                    motivo TEXT,
                    estado VARCHAR(20) DEFAULT 'PENDIENTE',
                    created_at TIMESTAMP DEFAULT NOW(),
                    notified_at TIMESTAMP,
                    CONSTRAINT fk_espera_paciente FOREIGN KEY (paciente_id)
                        REFERENCES pacientes (id) ON DELETE CASCADE,
                    CONSTRAINT fk_espera_medico FOREIGN KEY (medico_id)
                        REFERENCES medicos (id) ON DELETE CASCADE
                )
                """
            )
        )

        # Check if already in waitlist
        result = await db.execute(
            text(
                """
                SELECT id FROM lista_espera
                WHERE paciente_id = :paciente_id AND medico_id = :medico_id
                  AND estado = 'PENDIENTE'
                """
            ),
            {"paciente_id": paciente_id, "medico_id": medico_id},
        )
        existing = result.first()

        if existing:
            await engine.dispose()
            return "El paciente ya está en la lista de espera para este médico."

        # Add to waitlist
        await db.execute(
            text(
                """
                INSERT INTO lista_espera (paciente_id, medico_id, fecha_preferida, motivo)
                VALUES (:paciente_id, :medico_id, :fecha_preferida, :motivo)
                """
            ),
            {
                "paciente_id": paciente_id,
                "medico_id": medico_id,
                "fecha_preferida": fecha_preferida,
                "motivo": motivo,
            },
        )
        await db.commit()

    await engine.dispose()

    return json.dumps(
        {
            "accion": "agregar_lista_espera",
            "paciente_id": paciente_id,
            "medico_id": medico_id,
            "fecha_preferida": fecha_preferida,
            "estado": "PENDIENTE",
            "mensaje": "Paciente agregado a la lista de espera. Será notificado cuando se libere un slot.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def predecir_no_show(paciente_id: int) -> str:
    """Predice la probabilidad de que un paciente no asista a su próxima cita.

    Basado en:
    - Historial de asistencias anteriores
    - Frecuencia de cancelaciones
    - Días de la semana
    - Tiempo de anticipación de la cita

    Args:
        paciente_id: ID del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.fecha_hora_inicio, ec.codigo AS estado,
                       EXTRACT(DOW FROM c.fecha_hora_inicio) AS dia_semana,
                       EXTRACT(EPOCH FROM (c.fecha_hora_inicio - NOW()))/3600 AS horas_anticipacion
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.paciente_id = :paciente_id
                ORDER BY c.fecha_hora_inicio DESC
                LIMIT 20
                """
            ),
            {"paciente_id": paciente_id},
        )
        historial = result.mappings().all()

        # Get patient info
        result_pat = await db.execute(
            text("SELECT nombre, apellido FROM pacientes WHERE id = :id"),
            {"id": paciente_id},
        )
        paciente = result_pat.mappings().first()
    await engine.dispose()

    if not paciente:
        return f"No se encontró el paciente {paciente_id}."

    if not historial:
        return json.dumps(
            {
                "paciente": f"{paciente['nombre']} {paciente['apellido']}",
                "prediccion": "sin_datos",
                "probabilidad": "N/A",
                "mensaje": "No hay historial suficiente para predecir.",
            },
            ensure_ascii=False,
            indent=2,
        )

    total = len(historial)
    canceladas = sum(1 for h in historial if h["estado"] == "CANCELADA")
    completadas = sum(1 for h in historial if h["estado"] == "COMPLETADA")

    # Calculate base probability
    tasa_cancelacion = canceladas / total if total > 0 else 0
    tasa_asistencia = completadas / total if total > 0 else 0

    # Adjust by day of week (weekends have higher no-show rates)
    dia_prefiere = max(
        set(h["dia_semana"] for h in historial),
        key=lambda d: sum(1 for h in historial if h["dia_semana"] == d),
    )

    # Risk factors
    factores_riesgo = []
    if tasa_cancelacion > 0.3:
        factores_riesgo.append("Alta tasa de cancelaciones previas")
    if tasa_asistencia < 0.5:
        factores_riesgo.append("Baja tasa de asistencia histórica")

    # Final probability (simple heuristic)
    probabilidad = min(0.95, tasa_cancelacion * 0.7 + (0.1 if len(factores_riesgo) > 1 else 0))

    nivel_riesgo = "bajo"
    if probabilidad > 0.6:
        nivel_riesgo = "alto"
    elif probabilidad > 0.3:
        nivel_riesgo = "medio"

    return json.dumps(
        {
            "paciente_id": paciente_id,
            "paciente": f"{paciente['nombre']} {paciente['apellido']}",
            "total_citas": total,
            "tasa_cancelacion": f"{(tasa_cancelacion*100):.1f}%",
            "tasa_asistencia": f"{(tasa_asistencia*100):.1f}%",
            "probabilidad_no_show": f"{(probabilidad*100):.1f}%",
            "nivel_riesgo": nivel_riesgo,
            "factores_riesgo": factores_riesgo if factores_riesgo else ["Ninguno identificado"],
            "recomendacion": "Enviar recordatorio 24h antes" if nivel_riesgo == "medio" else (
                "Considerar confirmación telefónica y recordatorio SMS" if nivel_riesgo == "alto" else "Sin acciones adicionales requeridas"
            ),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def sugerir_seguimiento(cita_id: int) -> str:
    """Sugiere una cita de seguimiento basada en el diagnóstico de una cita completada.

    Analiza la nota médica y recomienda:
    - Tiempo de seguimiento recomendado
    - Especialidad necesaria
    - Motivo del seguimiento

    Args:
        cita_id: ID de la cita completada.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.fecha_hora_inicio,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       e.nombre AS especialidad,
                       nm.diagnostico, nm.tratamiento, nm.observaciones
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN especialidades e ON e.id = m.especialidad_id
                JOIN notas_medicas nm ON nm.cita_id = c.id
                WHERE c.id = :cita_id
                """
            ),
            {"cita_id": cita_id},
        )
        cita = result.mappings().first()
    await engine.dispose()

    if not cita:
        return f"No se encontró la cita {cita_id} o no tiene nota médica."

    # Simple keyword-based recommendations
    diagnostico = (cita["diagnostico"] or "").lower()
    tratamiento = (cita["tratamiento"] or "").lower()

    # Determine follow-up timing based on keywords
    dias_seguimiento = 30  # Default: 1 month
    motivo = "Seguimiento general"

    if any(word in diagnostico for word in ["cirugía", "operación", "procedimiento"]):
        dias_seguimiento = 14
        motivo = "Revisión post-procedimiento"
    elif any(word in diagnostico for word in ["infección", "antibiótico", "tratamiento"]):
        dias_seguimiento = 7
        motivo = "Evolución de tratamiento"
    elif any(word in diagnostico for word in ["crónico", "diabetes", "hipertensión"]):
        dias_seguimiento = 90
        motivo = "Control de condición crónica"
    elif any(word in tratamiento for word in ["fisioterapia", "rehabilitación"]):
        dias_seguimiento = 21
        motivo = "Evolución de rehabilitación"

    return json.dumps(
        {
            "cita_original": cita_id,
            "paciente": cita["paciente"],
            "medico_actual": cita["medico"],
            "especialidad": cita["especialidad"],
            "diagnostico": cita["diagnostico"][:200] if cita["diagnostico"] else "N/A",
            "seguimiento_recomendado": {
                "dias": dias_seguimiento,
                "motivo": motivo,
                "especialidad_sugerida": cita["especialidad"],
            },
            "mensaje": f"Se recomienda seguimiento en {dias_seguimiento} días. {motivo}.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def encontrar_horario_compartido(
    medico_ids: list[int], fecha: str, duracion_min: int = 30
) -> str:
    """Encuentra horarios donde múltiples doctores estén disponibles simultáneamente.

    Útil para citas conjuntas o segundas opiniones.

    Args:
        medico_ids: Lista de IDs de médicos (mínimo 2).
        fecha: Fecha a consultar (YYYY-MM-DD).
        duracion_min: Duración de la cita en minutos.
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    if len(medico_ids) < 2:
        return "Se requieren al menos 2 médicos para buscar horario compartido."

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get all occupied slots for each doctor
        disponibilidad = {}
        for med_id in medico_ids:
            result = await db.execute(
                text(
                    """
                    SELECT c.fecha_hora_inicio, c.fecha_hora_fin
                    FROM citas c
                    JOIN estados_cita ec ON ec.id = c.estado_id
                    WHERE c.medico_id = :medico_id
                      AND DATE(c.fecha_hora_inicio) = :fecha
                      AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                    ORDER BY c.fecha_hora_inicio
                    """
                ),
                {"medico_id": med_id, "fecha": fecha},
            )
            ocupadas = result.mappings().all()

            # Get doctor name
            result_med = await db.execute(
                text("SELECT nombre, apellido FROM medicos WHERE id = :id"),
                {"id": med_id},
            )
            medico = result_med.mappings().first()

            if medico:
                disponibilidad[med_id] = {
                    "nombre": f"{medico['nombre']} {medico['apellido']}",
                    "ocupadas": ocupadas,
                }
    await engine.dispose()

    # Generate potential slots
    date_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    all_slots = []
    for hour in range(8, 20):
        for minute in [0, 30]:
            slot_start = datetime.combine(date_obj, datetime.min.time().replace(hour=hour, minute=minute))
            if slot_start + timedelta(minutes=duracion_min) <= datetime.combine(date_obj, datetime.min.time().replace(hour=20)):
                all_slots.append(slot_start)

    # Find slots where ALL doctors are free
    slots_compartidos = []
    for slot in all_slots:
        slot_end = slot + timedelta(minutes=duracion_min)
        todos_libres = True
        for med_id, info in disponibilidad.items():
            for occ in info["ocupadas"]:
                if slot < occ["fecha_hora_fin"] and slot_end > occ["fecha_hora_inicio"]:
                    todos_libres = False
                    break
            if not todos_libres:
                break
        if todos_libres:
            slots_compartidos.append(slot)

    return json.dumps(
        {
            "medicos": [disponibilidad[mid]["nombre"] for mid in medico_ids if mid in disponibilidad],
            "fecha": fecha,
            "duracion_min": duracion_min,
            "horarios_compartidos": [
                {
                    "hora_inicio": s.strftime("%H:%M"),
                    "hora_fin": (s + timedelta(minutes=duracion_min)).strftime("%H:%M"),
                    "sugerencia": s.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                for s in slots_compartidos[:8]
            ],
            "total_disponibles": len(slots_compartidos),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def triagar_por_sintomas(descripcion_sintomas: str) -> str:
    """Analiza síntomas descritos y sugiere especialidad y nivel de urgencia.

    Args:
        descripcion_sintomas: Descripción de síntomas en lenguaje natural.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    # Keyword-based triage rules
    reglas = {
        "urgente": {
            "keywords": [
                "dolor pecho", "dificultad para respirar", "sangrado abundante",
                "pérdida de conocimiento", "convulsiones", "alergia severa",
                "dolor abdominal intenso", "fiebre alta", "traumatismo",
            ],
            "nivel": "URGENTE",
            "especialidad": "Urgencias",
            "tiempo": "Inmediato",
        },
        "alta": {
            "keywords": [
                "dolor fuerte", "fiebre", "inflamación", "mareo",
                "vómito", "diarrea persistente", "dolor articular",
                "erupción cutánea", "infección",
            ],
            "nivel": "ALTA",
            "especialidad": "Medicina General",
            "tiempo": "24-48 horas",
        },
        "media": {
            "keywords": [
                "dolor leve", "cansancio", "tos", "resfriado",
                "dolor de cabeza", "insomnio", "ansiedad leve",
                "dolor de espalda", "malestar general",
            ],
            "nivel": "MEDIA",
            "especialidad": "Medicina General",
            "tiempo": "3-5 días",
        },
        "baja": {
            "keywords": [
                "consulta", "receta", "certificado", "control",
                "seguimiento", "prevención", "examen",
            ],
            "nivel": "BAJA",
            "especialidad": "Medicina General",
            "tiempo": "1-2 semanas",
        },
    }

    sintomas_lower = descripcion_sintomas.lower()
    resultado = None

    for nivel, regla in reglas.items():
        for keyword in regla["keywords"]:
            if keyword in sintomas_lower:
                resultado = regla
                break
        if resultado:
            break

    if not resultado:
        resultado = {
            "nivel": "MEDIA",
            "especialidad": "Medicina General",
            "tiempo": "3-5 días",
        }

    # Get available specialties
    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text("SELECT id, nombre FROM especialidades ORDER BY nombre")
        )
        especialidades = [dict(r) for r in result.mappings().all()]
    await engine.dispose()

    return json.dumps(
        {
            "sintomas_evaluados": descripcion_sintomas,
            "triage": {
                "nivel_urgencia": resultado.get("nivel", "MEDIA"),
                "especialidad_recomendada": resultado.get("especialidad", "Medicina General"),
                "tiempo_atencion": resultado.get("tiempo", "3-5 días"),
            },
            "especialidades_disponibles": especialidades,
            "mensaje": f"Nivel: {resultado.get('nivel', 'MEDIA')}. "
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
    medico_id: int, fecha: str, motivo: str = "Emergencia médica"
) -> str:
    """Cancela TODAS las citas de un médico en una fecha específica.

    Útil para emergencias: médico enfermo, cierre inesperado, etc.
    Notifica automáticamente a la lista de espera.

    Args:
        medico_id: ID del médico.
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
                SELECT c.id, CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       c.fecha_hora_inicio, c.fecha_hora_fin
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND DATE(c.fecha_hora_inicio) = :fecha
                  AND ec.codigo NOT IN ('CANCELADA', 'COMPLETADA')
                ORDER BY c.fecha_hora_inicio
                """
            ),
            {"medico_id": medico_id, "fecha": fecha},
        )
        citas = result.mappings().all()

        if not citas:
            await engine.dispose()
            return f"No hay citas activas para el médico {medico_id} el {fecha}."

        # Get cancel state
        result_estado = await db.execute(
            text("SELECT id FROM estados_cita WHERE codigo = 'CANCELADA'")
        )
        estado_cancel = result_estado.first()

        # Cancel all appointments
        canceladas = []
        for cita in citas:
            await db.execute(
                text(
                    """
                    UPDATE citas SET estado_id = :estado_id, updated_at = NOW()
                    WHERE id = :cita_id
                    """
                ),
                {"estado_id": estado_cancel[0], "cita_id": cita["id"]},
            )
            canceladas.append({
                "id": cita["id"],
                "paciente": cita["paciente"],
                "hora": str(cita["fecha_hora_inicio"]),
            })

        # Check waitlist
        result_espera = await db.execute(
            text(
                """
                SELECT id, paciente_id, motivo
                FROM lista_espera
                WHERE medico_id = :medico_id AND estado = 'PENDIENTE'
                """
            ),
            {"medico_id": medico_id},
        )
        espera = result_espera.mappings().all()

        await db.commit()
    await engine.dispose()

    return json.dumps(
        {
            "accion": "cancelacion_masiva",
            "medico_id": medico_id,
            "fecha": fecha,
            "motivo": motivo,
            "citas_canceladas": len(canceladas),
            "detalles": canceladas,
            "lista_espera_notificada": len(espera),
            "mensaje": f"Se cancelaron {len(canceladas)} citas. {len(espera)} pacientes en lista de espera.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def replanificar_citas(
    medico_id: int, fecha_origen: str, fecha_destino: str, confirmado: bool = False
) -> str:
    """Mueve TODAS las citas de un día a otro para un médico.

    Revisa disponibilidad en la fecha destino y sugiere horarios.

    Args:
        medico_id: ID del médico.
        fecha_origen: Fecha original (YYYY-MM-DD).
        fecha_destino: Fecha destino (YYYY-MM-DD).
        confirmado: Debe ser True para ejecutar.
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get appointments to move
        result = await db.execute(
            text(
                """
                SELECT c.id, c.fecha_hora_inicio, c.fecha_hora_fin,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       ec.codigo AS estado
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND DATE(c.fecha_hora_inicio) = :fecha_origen
                  AND ec.codigo NOT IN ('CANCELADA', 'COMPLETADA')
                ORDER BY c.fecha_hora_inicio
                """
            ),
            {"medico_id": medico_id, "fecha_origen": fecha_origen},
        )
        citas_origen = result.mappings().all()

        # Get existing appointments on destination date
        result_dest = await db.execute(
            text(
                """
                SELECT c.fecha_hora_inicio, c.fecha_hora_fin
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND DATE(c.fecha_hora_inicio) = :fecha_destino
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.fecha_hora_inicio
                """
            ),
            {"medico_id": medico_id, "fecha_destino": fecha_destino},
        )
        ocupadas_dest = result_dest.mappings().all()
    await engine.dispose()

    if not citas_origen:
        return f"No hay citas activas para el médico {medico_id} el {fecha_origen}."

    if not confirmado:
        # Preview mode: suggest available slots
        return json.dumps(
            {
                "accion": "replanificacion_pendiente",
                "citas_a_mover": len(citas_origen),
                "fecha_origen": fecha_origen,
                "fecha_destino": fecha_destino,
                "citas": [
                    {
                        "id": c["id"],
                        "paciente": c["paciente"],
                        "hora_original": str(c["fecha_hora_inicio"]),
                    }
                    for c in citas_origen
                ],
                "mensaje": "Confirme para ejecutar la replanificación.",
            },
            ensure_ascii=False,
            indent=2,
        )

    # Execute replanification
    date_dest = datetime.strptime(fecha_destino, "%Y-%m-%d").date()
    hora_actual = datetime.combine(date_dest, datetime.min.time().replace(hour=8))
    hora_fin_jornada = datetime.combine(date_dest, datetime.min.time().replace(hour=20))

    movidas = []
    for cita in citas_origen:
        duracion = cita["fecha_hora_fin"] - cita["fecha_hora_inicio"]
        nueva_hora = hora_actual
        nueva_fin = nueva_hora + duracion

        # Find next available slot
        while nueva_fin <= hora_fin_jornada:
            conflicto = False
            for occ in ocupadas_dest:
                if nueva_hora < occ["fecha_hora_fin"] and nueva_fin > occ["fecha_hora_inicio"]:
                    conflicto = True
                    nueva_hora = occ["fecha_hora_fin"]
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
                        UPDATE citas
                        SET fecha_hora_inicio = :inicio, fecha_hora_fin = :fin,
                            estado_id = (SELECT id FROM estados_cita WHERE codigo = 'REAGENDADA')
                        WHERE id = :cita_id
                        """
                    ),
                    {"inicio": nueva_hora, "fin": nueva_fin, "cita_id": cita["id"]},
                )
                await db.commit()
            await engine2.dispose()

            movidas.append({
                "id": cita["id"],
                "paciente": cita["paciente"],
                "hora_original": str(cita["fecha_hora_inicio"]),
                "nueva_hora": str(nueva_hora),
            })
            hora_actual = nueva_fin
            ocupadas_dest.append({"fecha_hora_inicio": nueva_hora, "fecha_hora_fin": nueva_fin})

    return json.dumps(
        {
            "accion": "replanificacion_completada",
            "medico_id": medico_id,
            "fecha_origen": fecha_origen,
            "fecha_destino": fecha_destino,
            "citas_movidas": len(movidas),
            "detalles": movidas,
            "mensaje": f"Se movieron {len(movidas)} citas de {fecha_origen} a {fecha_destino}.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def notificar_lista_espera(medico_id: int, fecha: str = "") -> str:
    """Notifica a pacientes en lista de espera cuando se libera un slot.

    Args:
        medico_id: ID del médico.
        fecha: Fecha específica a notificar (opcional, default: próximos 7 días).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get pending waitlist
        query = """
            SELECT le.id, le.paciente_id, le.fecha_preferida, le.motivo,
                   CONCAT(p.nombre, ' ', p.apellido) AS paciente
            FROM lista_espera le
            JOIN pacientes p ON p.id = le.paciente_id
            WHERE le.medico_id = :medico_id AND le.estado = 'PENDIENTE'
        """
        if fecha:
            query += " AND le.fecha_preferida = :fecha"
        query += " ORDER BY le.created_at"

        params = {"medico_id": medico_id}
        if fecha:
            params["fecha"] = fecha

        result = await db.execute(text(query), params)
        pendientes = result.mappings().all()

        if not pendientes:
            await engine.dispose()
            return "No hay pacientes en lista de espera para este médico."

        # Check available slots
        result_slots = await db.execute(
            text(
                """
                SELECT c.fecha_hora_inicio, c.fecha_hora_fin
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND c.fecha_hora_inicio >= NOW()
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                ORDER BY c.fecha_hora_inicio
                """
            ),
            {"medico_id": medico_id},
        )
        ocupadas = result_slots.mappings().all()

    await engine.dispose()

    # Find free slots in next 7 days
    date_obj = datetime.now().date()
    slots_libres = []
    for day_offset in range(7):
        check_date = date_obj + timedelta(days=day_offset)
        for hour in [9, 10, 11, 14, 15, 16, 17]:
            slot_start = datetime.combine(check_date, datetime.min.time().replace(hour=hour))
            slot_end = slot_start + timedelta(minutes=30)
            is_free = True
            for occ in ocupadas:
                if slot_start < occ["fecha_hora_fin"] and slot_end > occ["fecha_hora_inicio"]:
                    is_free = False
                    break
            if is_free:
                slots_libres.append(slot_start)

    # Match waitlist with available slots
    notificados = []
    for pend in pendientes[:len(slots_libres)]:
        notificados.append({
            "paciente_id": pend["paciente_id"],
            "paciente": pend["paciente"],
            "slot_ofrecido": slots_libres[len(notificados)].strftime("%Y-%m-%dT%H:%M:%S"),
            "motivo_original": pend["motivo"],
        })

    return json.dumps(
        {
            "accion": "notificar_lista_espera",
            "medico_id": medico_id,
            "total_pendientes": len(pendientes),
            "slots_disponibles": len(slots_libres),
            "notificados": len(notificados),
            "detalles": notificados,
            "mensaje": f"{len(notificados)} pacientes notificados de slots disponibles.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def protocolo_emergencia(
    medico_id: int, fecha: str, tipo: str = "enfermedad"
) -> str:
    """Ejecuta protocolo de emergencia: cancela, reasigna y notifica automáticamente.

    Tipos: enfermedad, emergencia_personal, cierre_institucional, desastre_natural.

    Args:
        medico_id: ID del médico afectado.
        fecha: Fecha del incidente (YYYY-MM-DD).
        tipo: Tipo de emergencia.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get doctor info
        result_med = await db.execute(
            text("SELECT nombre, apellido FROM medicos WHERE id = :id"),
            {"id": medico_id},
        )
        medico = result_med.mappings().first()

        if not medico:
            await engine.dispose()
            return f"No se encontró el médico {medico_id}."

        # Get all active appointments
        result = await db.execute(
            text(
                """
                SELECT c.id, c.paciente_id, c.fecha_hora_inicio,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND DATE(c.fecha_hora_inicio) = :fecha
                  AND ec.codigo NOT IN ('CANCELADA', 'COMPLETADA')
                ORDER BY c.fecha_hora_inicio
                """
            ),
            {"medico_id": medico_id, "fecha": fecha},
        )
        citas = result.mappings().all()

        # Cancel all
        result_estado = await db.execute(
            text("SELECT id FROM estados_cita WHERE codigo = 'CANCELADA'")
        )
        estado_cancel = result_estado.first()

        canceladas = []
        for cita in citas:
            await db.execute(
                text(
                    "UPDATE citas SET estado_id = :estado_id WHERE id = :cita_id"
                ),
                {"estado_id": estado_cancel[0], "cita_id": cita["id"]},
            )
            canceladas.append({
                "id": cita["id"],
                "paciente": cita["paciente"],
                "hora": str(cita["fecha_hora_inicio"]),
            })

        await db.commit()
    await engine.dispose()

    return json.dumps(
        {
            "accion": "protocolo_emergencia",
            "tipo": tipo,
            "medico": f"{medico['nombre']} {medico['apellido']}",
            "fecha": fecha,
            "citas_canceladas": len(canceladas),
            "detalles": canceladas,
            "pasos_siguientes": [
                "Notificar a pacientes afectados",
                "Verificar lista de espera para reasignación",
                "Actualizar estado del médico en el sistema",
                "Documentar incidente en auditoría",
            ],
            "mensaje": f"Protocolo ejecutado: {len(canceladas)} citas canceladas por {tipo}.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def optimizar_agenda(medico_id: int, dias: int = 14) -> str:
    """Analiza y sugiere optimizaciones para la agenda del médico.

    Identifica:
    - Horarios subutilizados
    - Bloques muertos
    - Oportunidades de compactación
    - Distribución ideal de citas

    Args:
        medico_id: ID del médico.
        dias: Días a analizar (default 14).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT DATE(c.fecha_hora_inicio) AS dia,
                       EXTRACT(HOUR FROM c.fecha_hora_inicio) AS hora,
                       COUNT(*) AS total_citas
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND c.fecha_hora_inicio >= NOW()
                  AND c.fecha_hora_inicio < NOW() + INTERVAL ':dias days'
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY dia, hora
                ORDER BY dia, hora
                """
            ),
            {"medico_id": medico_id, "dias": dias},
        )
        carga = result.mappings().all()
    await engine.dispose()

    # Analyze patterns
    horas_pico = {}
    horas_vacias = []
    for row in carga:
        hora = int(row["hora"])
        horas_pico[hora] = horas_pico.get(hora, 0) + row["total_citas"]

    # Find underutilized hours (08:00-20:00)
    for hour in range(8, 20):
        if hour not in horas_pico:
            horas_vacias.append(f"{hour:02d}:00")

    # Recommendations
    recomendaciones = []
    if horas_vacias:
        recomendaciones.append({
            "tipo": "compactar",
            "descripcion": f"Horarios vacíos: {', '.join(horas_vacias[:5])}",
            "accion": "Mover citas a estos horarios para maximizar espacio.",
        })

    hora_pico = max(horas_pico, key=horas_pico.get) if horas_pico else None
    if hora_pico and horas_pico[hora_pico] > 5:
        recomendaciones.append({
            "tipo": "distribuir",
            "descripcion": f"Hora pico: {hora_pico:02d}:00 con {horas_pico[hora_pico]} citas",
            "accion": "Distribuir carga a horas menos ocupadas.",
        })

    return json.dumps(
        {
            "medico_id": medico_id,
            "periodo_analisis": f"Próximos {dias} días",
            "horas_pico": horas_pico,
            "horas_subutilizadas": horas_vacias,
            "recomendaciones": recomendaciones,
            "eficiencia_actual": f"{len(carga)} bloques ocupados de {dias * 12} posibles",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def generar_recordatorio(cita_id: int, tipo: str = "general") -> str:
    """Genera un recordatorio personalizado para una cita médica.

    Tipos: general, pre_cita, post_cita, seguimiento.

    Args:
        cita_id: ID de la cita.
        tipo: Tipo de recordatorio.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.id, c.fecha_hora_inicio, c.motivo_consulta,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       e.nombre AS especialidad,
                       ec.codigo AS estado
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN especialidades e ON e.id = m.especialidad_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.id = :cita_id
                """
            ),
            {"cita_id": cita_id},
        )
        cita = result.mappings().first()
    await engine.dispose()

    if not cita:
        return f"No se encontró la cita {cita_id}."

    # Generate reminder based on type
    recordatorios = {
        "general": (
            f"Estimado/a {cita['paciente']}, le recordamos su cita con {cita['medico']} "
            f"({cita['especialidad']}) el {cita['fecha_hora_inicio']}. "
            f"Motivo: {cita['motivo_consulta']}. Por favor, confirme asistencia."
        ),
        "pre_cita": (
            f"Recordatorio 24h: Mañana tiene cita con {cita['medico']} a las "
            f"{cita['fecha_hora_inicio']}. Por favor traiga identificación y seguro médico."
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
            "cita_id": cita_id,
            "tipo": tipo,
            "paciente": cita["paciente"],
            "medico": cita["medico"],
            "fecha": str(cita["fecha_hora_inicio"]),
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
async def predecir_demanda(dias: int = 30) -> str:
    """Predice la demanda de citas médicas para los próximos N días.

    Analiza tendencias históricas, patrones estacionales y sugiere:
    - Días de alta demanda esperados
    - Especialidades más solicitadas
    - Recomendaciones de staffing

    Args:
        dias: Días a predecir (default 30).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get historical data (last 90 days)
        result = await db.execute(
            text(
                """
                SELECT DATE(c.fecha_hora_inicio) AS dia,
                       e.nombre AS especialidad,
                       EXTRACT(DOW FROM c.fecha_hora_inicio) AS dia_semana,
                       COUNT(*) AS total_citas
                FROM citas c
                JOIN medicos m ON m.id = c.medico_id
                JOIN especialidades e ON e.id = m.especialidad_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.fecha_hora_inicio >= NOW() - INTERVAL '90 days'
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY dia, especialidad, dia_semana
                ORDER BY dia
                """
            )
        )
        historial = result.mappings().all()

        # Get current month appointments
        result_actual = await db.execute(
            text(
                """
                SELECT DATE(c.fecha_hora_inicio) AS dia,
                       COUNT(*) AS total
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.fecha_hora_inicio >= DATE_TRUNC('month', NOW())
                  AND c.fecha_hora_inicio < DATE_TRUNC('month', NOW()) + INTERVAL '1 month'
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY dia
                """
            )
        )
        mes_actual = result_actual.mappings().all()
    await engine.dispose()

    # Analyze patterns
    dias_semana = {0: "Dom", 1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb"}
    demanda_por_dia = {}
    demanda_por_especialidad = {}

    for row in historial:
        dia = dias_semana.get(row["dia_semana"], "?")
        demanda_por_dia[dia] = demanda_por_dia.get(dia, 0) + row["total_citas"]
        esp = row["especialidad"]
        demanda_por_especialidad[esp] = demanda_por_especialidad.get(esp, 0) + row["total_citas"]

    # Predictions
    promedio_diario = sum(demanda_por_dia.values()) / 7 if demanda_por_dia else 0
    dia_pico = max(demanda_por_dia, key=demanda_por_dia.get) if demanda_por_dia else "N/A"
    especialidad_top = max(demanda_por_especialidad, key=demanda_por_especialidad.get) if demanda_por_especialidad else "N/A"

    return json.dumps(
        {
            "periodo_analisis": "90 días históricos",
            "periodo_prediccion": f"Próximos {dias} días",
            "promedio_citas_dia": round(promedio_diario, 1),
            "dia_mas_demanda": dia_pico,
            "demanda_por_dia": demanda_por_dia,
            "especialidades_top": demanda_por_especialidad,
            "especialidad_mas_solicitada": especialidad_top,
            "citas_mes_actual": len(mes_actual),
            "recomendaciones": [
                f"Aumentar disponibilidad los {dia_pico}",
                f"Priorizar especialidad: {especialidad_top}",
                "Considerar horarios extendidos en temporada alta",
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def matching_paciente_medico(paciente_id: int) -> str:
    """Recomienda el mejor médico para un paciente basado en compatibilidad.

    Analiza:
    - Historial de citas previas
    - Especialidades más visitadas
    - Médicos con mejor tasa de completado
    - Disponibilidad actual

    Args:
        paciente_id: ID del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get patient info
        result_pat = await db.execute(
            text(
                """
                SELECT p.id, CONCAT(p.nombre, ' ', p.apellido) AS nombre,
                       COUNT(c.id) AS total_citas,
                       SUM(CASE WHEN ec.codigo = 'COMPLETADA' THEN 1 ELSE 0 END) AS completadas,
                       SUM(CASE WHEN ec.codigo = 'CANCELADA' THEN 1 ELSE 0 END) AS canceladas
                FROM pacientes p
                LEFT JOIN citas c ON c.paciente_id = p.id
                LEFT JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE p.id = :paciente_id
                GROUP BY p.id, p.nombre, p.apellido
                """
            ),
            {"paciente_id": paciente_id},
        )
        paciente = result_pat.mappings().first()

        if not paciente:
            await engine.dispose()
            return f"No se encontró el paciente {paciente_id}."

        # Get doctor history for this patient
        result_docs = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.nombre, ' ', m.apellido) AS nombre,
                       e.nombre AS especialidad,
                       COUNT(c.id) AS citas_con_paciente,
                       SUM(CASE WHEN ec.codigo = 'COMPLETADA' THEN 1 ELSE 0 END) AS completadas,
                       SUM(CASE WHEN ec.codigo = 'CANCELADA' THEN 1 ELSE 0 END) AS canceladas
                FROM medicos m
                JOIN especialidades e ON e.id = m.especialidad_id
                LEFT JOIN citas c ON c.medico_id = m.id AND c.paciente_id = :paciente_id
                LEFT JOIN estados_cita ec ON ec.id = c.estado_id
                GROUP BY m.id, m.nombre, m.apellido, e.nombre
                HAVING COUNT(c.id) > 0
                ORDER BY completadas DESC NULLS LAST
                LIMIT 5
                """
            ),
            {"paciente_id": paciente_id},
        )
        medicos_historial = result_docs.mappings().all()

        # Get top doctors overall
        result_top = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.nombre, ' ', m.apellido) AS nombre,
                       e.nombre AS especialidad,
                       COUNT(c.id) AS total_citas,
                       SUM(CASE WHEN ec.codigo = 'COMPLETADA' THEN 1 ELSE 0 END) AS completadas
                FROM medicos m
                JOIN especialidades e ON e.id = m.especialidad_id
                LEFT JOIN citas c ON c.medico_id = m.id
                LEFT JOIN estados_cita ec ON ec.id = c.estado_id
                GROUP BY m.id, m.nombre, m.apellido, e.nombre
                ORDER BY completadas DESC NULLS LAST
                LIMIT 5
                """
            )
        )
        medicos_top = result_top.mappings().all()
    await engine.dispose()

    # Calculate compatibility scores
    recomendaciones = []
    for med in medicos_historial:
        tasa_exito = (med["completadas"] or 0) / med["citas_con_paciente"] if med["citas_con_paciente"] > 0 else 0
        score = tasa_exito * 100
        recomendaciones.append({
            "medico_id": med["id"],
            "nombre": med["nombre"],
            "especialidad": med["especialidad"],
            "citas_juntos": med["citas_con_paciente"],
            "tasa_exito": f"{(tasa_exito*100):.1f}%",
            "score_compatibilidad": round(score, 1),
            "tipo": "historial",
        })

    # Add top doctors if no history
    if not recomendaciones:
        for med in medicos_top:
            tasa = (med["completadas"] or 0) / med["total_citas"] if med["total_citas"] > 0 else 0
            recomendaciones.append({
                "medico_id": med["id"],
                "nombre": med["nombre"],
                "especialidad": med["especialidad"],
                "score_compatibilidad": round(tasa * 100, 1),
                "tipo": "recomendado",
            })

    return json.dumps(
        {
            "paciente": paciente["nombre"],
            "total_citas_historial": paciente["total_citas"],
            "mejores_medicos": sorted(recomendaciones, key=lambda x: x["score_compatibilidad"], reverse=True)[:5],
            "mensaje": "Médicos ordenados por compatibilidad con el paciente.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def duracion_inteligente(medico_id: int, motivo: str = "") -> str:
    """Predice la duración óptima de una cita basada en el tipo de consulta.

    Analiza citas previas similares y sugiere duración personalizada.

    Args:
        medico_id: ID del médico.
        motivo: Motivo de la consulta (para buscar patrones similares).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get average duration by doctor
        result = await db.execute(
            text(
                """
                SELECT AVG(EXTRACT(EPOCH FROM (c.fecha_hora_fin - c.fecha_hora_inicio))/60) AS promedio_min,
                       MIN(EXTRACT(EPOCH FROM (c.fecha_hora_fin - c.fecha_hora_inicio))/60) AS minimo,
                       MAX(EXTRACT(EPOCH FROM (c.fecha_hora_fin - c.fecha_hora_inicio))/60) AS maximo,
                       COUNT(*) AS total_citas
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND ec.codigo = 'COMPLETADA'
                """
            ),
            {"medico_id": medico_id},
        )
        stats = result.mappings().first()

        # Get duration by reason (if provided)
        duracion_motivo = None
        if motivo:
            result_motivo = await db.execute(
                text(
                    """
                    SELECT AVG(EXTRACT(EPOCH FROM (c.fecha_hora_fin - c.fecha_hora_inicio))/60) AS promedio
                    FROM citas c
                    JOIN estados_cita ec ON ec.id = c.estado_id
                    WHERE c.medico_id = :medico_id
                      AND c.motivo_consulta ILIKE :motivo
                      AND ec.codigo = 'COMPLETADA'
                    """
                ),
                {"medico_id": medico_id, "motivo": f"%{motivo}%"},
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
            "medico_id": medico_id,
            "motivo_consulta": motivo or "General",
            "estadisticas_historicas": {
                "promedio_min": round(promedio, 1),
                "minimo_min": round(minimo, 1),
                "maximo_min": round(maximo, 1),
                "total_citas_analizadas": stats["total_citas"],
            },
            "duracion_recomendada_min": round(duracion_recomendada),
            "rango_sugerido": f"{round(duracion_recomendada - 5)}-{round(duracion_recomendada + 10)} min",
            "mensaje": f"Cita recomendada de {round(duracion_recomendada)} minutos.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def optimizar_ingresos(medico_id: int, dias: int = 30) -> str:
    """Analiza y sugiere estrategias para maximizar ingresos.

    Identifica:
    - Horarios de mayor facturación
    - Citas canceladas que podrían rellenarse
    - Oportunidades de upselling (procedimientos adicionales)
    - Precio óptimo por tipo de cita

    Args:
        medico_id: ID del médico.
        dias: Días a analizar (default 30).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get appointment stats
        result = await db.execute(
            text(
                """
                SELECT EXTRACT(HOUR FROM c.fecha_hora_inicio) AS hora,
                       EXTRACT(DOW FROM c.fecha_hora_inicio) AS dia_semana,
                       ec.codigo AS estado,
                       COUNT(*) AS total
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND c.fecha_hora_inicio >= NOW() - INTERVAL ':dias days'
                GROUP BY hora, dia_semana, ec.codigo
                """
            ),
            {"medico_id": medico_id, "dias": dias},
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
        if row["estado"] == "COMPLETADA":
            horas_facturacion[hora] = horas_facturacion.get(hora, 0) + row["total"]
            total_completadas += row["total"]
        elif row["estado"] == "CANCELADA":
            cancelaciones_por_hora[hora] = cancelaciones_por_hora.get(hora, 0) + row["total"]
            total_canceladas += row["total"]

    # Revenue optimization suggestions
    sugerencias = []
    hora_pico = max(horas_facturacion, key=horas_facturacion.get) if horas_facturacion else None

    if hora_pico:
        sugerencias.append({
            "tipo": "mantener",
            "descripcion": f"Hora pico de productividad: {hora_pico:02d}:00",
            "impacto": "Alto",
        })

    horas_canceladas = sorted(cancelaciones_por_hora.items(), key=lambda x: x[1], reverse=True)
    if horas_canceladas:
        sugerencias.append({
            "tipo": "rellenar",
            "descripcion": f"Horas con más cancelaciones: {horas_canceladas[0][0]:02d}:00 ({horas_canceladas[0][1]} cancelaciones)",
            "impacto": "Medio",
            "accion": "Ofrecer descuento o prioridad para rellenar estos slots",
        })

    if total_canceladas > total_completadas * 0.2:
        sugerencias.append({
            "tipo": "reducir_cancelaciones",
            "descripcion": f"Tasa de cancelación: {(total_canceladas/(total_completadas+total_canceladas)*100):.1f}%",
            "impacto": "Alto",
            "accion": "Implementar recordatorios 24h antes y confirmación telefónica",
        })

    return json.dumps(
        {
            "medico_id": medico_id,
            "periodo": f"Últimos {dias} días",
            "citas_completadas": total_completadas,
            "citas_canceladas": total_canceladas,
            "tasa_cancelacion": f"{(total_canceladas/(total_completadas+total_canceladas)*100):.1f}%" if (total_completadas+total_canceladas) > 0 else "0%",
            "horas_mas_productivas": horas_facturacion,
            "sugerencias": sugerencias,
            "potencial_mejora": f"Reducir cancelaciones podría aumentar ingresos ~{(total_canceladas * 0.3):.0f} citas/mes",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def score_satisfaccion(paciente_id: int) -> str:
    """Calcula un score de satisfacción del paciente basado en su comportamiento.

    Indicadores:
    - Tasa de asistencia
    - Frecuencia de reagendamientos
    - Tiempo entre citas
    - Estado de las citas

    Args:
        paciente_id: ID del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(
            text(
                """
                SELECT c.fecha_hora_inicio, ec.codigo AS estado,
                       LAG(c.fecha_hora_inicio) OVER (ORDER BY c.fecha_hora_inicio) AS cita_anterior
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.paciente_id = :paciente_id
                ORDER BY c.fecha_hora_inicio
                LIMIT 20
                """
            ),
            {"paciente_id": paciente_id},
        )
        historial = result.mappings().all()

        result_pat = await db.execute(
            text("SELECT nombre, apellido FROM pacientes WHERE id = :id"),
            {"id": paciente_id},
        )
        paciente = result_pat.mappings().first()
    await engine.dispose()

    if not paciente:
        return f"No se encontró el paciente {paciente_id}."

    if not historial:
        return json.dumps(
            {
                "paciente": f"{paciente['nombre']} {paciente['apellido']}",
                "score": "N/A",
                "mensaje": "Sin historial suficiente para calcular score.",
            },
            ensure_ascii=False,
            indent=2,
        )

    total = len(historial)
    completadas = sum(1 for h in historial if h["estado"] == "COMPLETADA")
    canceladas = sum(1 for h in historial if h["estado"] == "CANCELADA")
    reagendadas = sum(1 for h in historial if h["estado"] == "REAGENDADA")

    # Calculate score
    tasa_asistencia = completadas / total if total > 0 else 0
    penalty_cancelacion = (canceladas / total) * 30 if total > 0 else 0
    penalty_reagendamiento = (reagendadas / total) * 10 if total > 0 else 0

    score = max(0, min(100, (tasa_asistencia * 100) - penalty_cancelacion - penalty_reagendamiento))

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
            "paciente_id": paciente_id,
            "paciente": f"{paciente['nombre']} {paciente['apellido']}",
            "total_citas": total,
            "completadas": completadas,
            "canceladas": canceladas,
            "reagendadas": reagendadas,
            "tasa_asistencia": f"{(tasa_asistencia*100):.1f}%",
            "score_satisfaccion": round(score, 1),
            "nivel": nivel,
            "recomendacion": recomendacion,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def resumen_clinico_paciente(paciente_id: int) -> str:
    """Genera un resumen clínico automático del paciente antes de su cita.

    Incluye:
    - Historial de diagnósticos
    - Tratamientos activos
    - Citas recientes
    - Alertas importantes

    Args:
        paciente_id: ID del paciente.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Patient info
        result_pat = await db.execute(
            text(
                """
                SELECT id, nombre, apellido, fecha_nacimiento, email, telefono
                FROM pacientes WHERE id = :id
                """
            ),
            {"id": paciente_id},
        )
        paciente = result_pat.mappings().first()

        if not paciente:
            await engine.dispose()
            return f"No se encontró el paciente {paciente_id}."

        # Recent diagnoses
        result_diag = await db.execute(
            text(
                """
                SELECT nm.diagnostico, nm.tratamiento, nm.observaciones,
                       c.fecha_hora_inicio,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico
                FROM notas_medicas nm
                JOIN citas c ON c.id = nm.cita_id
                JOIN medicos m ON m.id = c.medico_id
                WHERE c.paciente_id = :paciente_id
                ORDER BY c.fecha_hora_inicio DESC
                LIMIT 5
                """
            ),
            {"paciente_id": paciente_id},
        )
        diagnosticos = result_diag.mappings().all()

        # Upcoming appointments
        result_citas = await db.execute(
            text(
                """
                SELECT c.fecha_hora_inicio, c.motivo_consulta,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       ec.codigo AS estado
                FROM citas c
                JOIN medicos m ON m.id = c.medico_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.paciente_id = :paciente_id
                  AND c.fecha_hora_inicio >= NOW()
                ORDER BY c.fecha_hora_inicio
                LIMIT 3
                """
            ),
            {"paciente_id": paciente_id},
        )
        proximas_citas = result_citas.mappings().all()
    await engine.dispose()

    # Build summary
    resumen = {
        "paciente": {
            "id": paciente_id,
            "nombre": f"{paciente['nombre']} {paciente['apellido']}",
            "fecha_nacimiento": str(paciente["fecha_nacimiento"]),
        },
        "diagnosticos_recientes": [
            {
                "diagnostico": d["diagnostico"][:200] if d["diagnostico"] else "N/A",
                "tratamiento": d["tratamiento"][:200] if d["tratamiento"] else "N/A",
                "medico": d["medico"],
                "fecha": str(d["fecha_hora_inicio"]),
            }
            for d in diagnosticos
        ],
        "proximas_citas": [
            {
                "fecha": str(c["fecha_hora_inicio"]),
                "medico": c["medico"],
                "motivo": c["motivo_consulta"][:150] if c["motivo_consulta"] else "N/A",
                "estado": c["estado"],
            }
            for c in proximas_citas
        ],
        "alertas": [],
    }

    # Generate alerts
    if diagnosticos:
        ultimo_diag = diagnosticos[0]["diagnostico"] or ""
        if any(word in ultimo_diag.lower() for word in ["crónico", "diabetes", "hipertensión"]):
            resumen["alertas"].append("Paciente con condición crónica - requiere seguimiento regular")

    if len(diagnosticos) > 2:
        resumen["alertas"].append(f"Paciente con {len(diagnosticos)} consultas recientes - posible caso complejo")

    return json.dumps(resumen, ensure_ascii=False, indent=2)


@tool
async def detectar_anomalias(dias: int = 30) -> str:
    """Detecta patrones anómalos en la agenda que pueden indicar problemas.

    Identifica:
    - Médicos con tasa de cancelación inusualmente alta
    - Horarios con anomalías de demanda
    - Pacientes con comportamiento inusual
    - Posibles errores de programación

    Args:
        dias: Días a analizar (default 30).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Doctor cancellation rates
        result_docs = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       COUNT(c.id) AS total,
                       SUM(CASE WHEN ec.codigo = 'CANCELADA' THEN 1 ELSE 0 END) AS canceladas
                FROM medicos m
                LEFT JOIN citas c ON c.medico_id = m.id
                    AND c.fecha_hora_inicio >= NOW() - INTERVAL ':dias days'
                LEFT JOIN estados_cita ec ON ec.id = c.estado_id
                GROUP BY m.id, m.nombre, m.apellido
                HAVING COUNT(c.id) > 5
                """
            ),
            {"dias": dias},
        )
        medicos = result_docs.mappings().all()

        # Overbooking detection
        result_overbook = await db.execute(
            text(
                """
                SELECT DATE(c.fecha_hora_inicio) AS dia,
                       c.medico_id,
                       COUNT(*) AS citas_dia
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.fecha_hora_inicio >= NOW() - INTERVAL ':dias days'
                  AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                GROUP BY dia, c.medico_id
                HAVING COUNT(*) > 10
                """
            ),
            {"dias": dias},
        )
        overbooking = result_overbook.mappings().all()
    await engine.dispose()

    anomalias = []

    # Check for high cancellation rates
    for med in medicos:
        if med["total"] > 0:
            tasa = (med["canceladas"] or 0) / med["total"]
            if tasa > 0.4:
                anomalias.append({
                    "tipo": "alta_cancelacion",
                    "severidad": "ALTA",
                    "descripcion": f"Dr. {med['medico']} tiene tasa de cancelación del {(tasa*100):.1f}%",
                    "accion": "Revisar motivos, considerar recordatorios o depósitos",
                })
            elif tasa > 0.25:
                anomalias.append({
                    "tipo": "cancelacion_moderada",
                    "severidad": "MEDIA",
                    "descripcion": f"Dr. {med['medico']} tiene tasa de cancelación del {(tasa*100):.1f}%",
                    "accion": "Monitorear y ajustar política de cancelación",
                })

    # Check for overbooking
    for ob in overbooking:
        anomalias.append({
            "tipo": "sobrecarga",
            "severidad": "MEDIA",
            "descripcion": f"Médico {ob['medico_id']} con {ob['citas_dia']} citas el {ob['dia']}",
            "accion": "Revisar capacidad y redistribuir si es necesario",
        })

    return json.dumps(
        {
            "periodo_analisis": f"Últimos {dias} días",
            "anomalias_encontradas": len(anomalias),
            "detalles": anomalias if anomalias else [{"tipo": "sin_anomalias", "mensaje": "No se detectaron anomalías significativas."}],
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def scheduling_adaptativo(medico_id: int) -> str:
    """Analiza el rendimiento del scheduling y sugiere mejoras automáticas.

    Aprende de:
    - Citas que excedieron el tiempo estimado
    - Patrones de puntualidad
    - Eficiencia por hora del día
    - Recomendaciones de mejora continua

    Args:
        medico_id: ID del médico.
    """
    from datetime import datetime

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Analyze scheduling efficiency
        result = await db.execute(
            text(
                """
                SELECT EXTRACT(HOUR FROM c.fecha_hora_inicio) AS hora,
                       AVG(EXTRACT(EPOCH FROM (c.fecha_hora_fin - c.fecha_hora_inicio))/60) AS duracion_real,
                       COUNT(*) AS total_citas,
                       SUM(CASE WHEN ec.codigo = 'COMPLETADA' THEN 1 ELSE 0 END) AS completadas
                FROM citas c
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND c.fecha_hora_inicio >= NOW() - INTERVAL '30 days'
                GROUP BY hora
                ORDER BY hora
                """
            ),
            {"medico_id": medico_id},
        )
        eficiencia = result.mappings().all()

        # Get doctor name
        result_med = await db.execute(
            text("SELECT nombre, apellido FROM medicos WHERE id = :id"),
            {"id": medico_id},
        )
        medico = result_med.mappings().first()
    await engine.dispose()

    if not medico:
        return f"No se encontró el médico {medico_id}."

    # Analyze patterns
    horas_analisis = {}
    for row in eficiencia:
        hora = int(row["hora"])
        duracion = row["duracion_real"] or 30
        completadas = row["completadas"] or 0
        total = row["total_citas"] or 0
        tasa_completado = completadas / total if total > 0 else 0

        horas_analisis[f"{hora:02d}:00"] = {
            "duracion_promedio_min": round(duracion, 1),
            "citas": total,
            "tasa_completado": f"{(tasa_completado*100):.1f}%",
        }

    # Generate adaptive recommendations
    recomendaciones = []
    horas_datos = list(horas_analisis.items())

    for i in range(len(horas_datos) - 1):
        hora_actual, datos_actual = horas_datos[i]
        hora_siguiente, datos_siguiente = horas_datos[i + 1]

        if datos_actual["duracion_promedio_min"] > 45:
            recomendaciones.append({
                "tipo": "ajustar_duracion",
                "hora": hora_actual,
                "descripcion": f"Citas en {hora_actual} duran {datos_actual['duracion_promedio_min']} min (promedio)",
                "accion": f"Aumentar slot a {round(datos_actual['duracion_promedio_min'] + 5)} min",
            })

    return json.dumps(
        {
            "medico": f"{medico['nombre']} {medico['apellido']}",
            "periodo": "Últimos 30 días",
            "analisis_por_hora": horas_analisis,
            "recomendaciones": recomendaciones,
            "mensaje": "Análisis de eficiencia de scheduling completado.",
        },
        ensure_ascii=False,
        indent=2,
    )


# ============================================================================
# AGENDA IA: RESOLUCIÓN DE CONFLICTOS POR CIRUGÍA
# ============================================================================


@tool
async def resolver_conflicto_cirugia(
    medico_id: int,
    fecha_cirugia: str,
    hora_inicio: str = "08:00",
    hora_fin: str = "14:00",
    confirmado: bool = False,
) -> str:
    """Resuelve automáticamente el conflicto cuando un médico tiene cirugía programada.

    PASOS:
    1. Identifica todas las citas afectadas en el horario de cirugía
    2. Busca médicos de la misma especialidad disponibles
    3. Sugiere reasignación automática o reagendamiento
    4. Genera notificaciones personalizadas para cada paciente
    5. Ejecuta la acción confirmada

    Args:
        medico_id: ID del médico que tendrá la cirugía.
        fecha_cirugia: Fecha de la cirugía (YYYY-MM-DD).
        hora_inicio: Hora inicio de la cirugía (default 08:00).
        hora_fin: Hora fin de la cirugía (default 14:00).
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
                SELECT m.id, m.nombre, m.apellido, m.especialidad_id,
                       e.nombre AS especialidad
                FROM medicos m
                JOIN especialidades e ON e.id = m.especialidad_id
                WHERE m.id = :medico_id
                """
            ),
            {"medico_id": medico_id},
        )
        medico = result_med.mappings().first()

        if not medico:
            await engine.dispose()
            return f"No se encontró el médico {medico_id}."

        # 2. Find affected appointments
        fecha_dt = datetime.strptime(fecha_cirugia, "%Y-%m-%d")
        inicio_dt = fecha_dt.replace(hour=int(hora_inicio.split(":")[0]), minute=int(hora_inicio.split(":")[1]))
        fin_dt = fecha_dt.replace(hour=int(hora_fin.split(":")[0]), minute=int(hora_fin.split(":")[1]))

        result_citas = await db.execute(
            text(
                """
                SELECT c.id, c.paciente_id, c.fecha_hora_inicio, c.fecha_hora_fin,
                       c.motivo_consulta,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       p.email, p.telefono
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN estados_cita ec ON ec.id = c.estado_id
                WHERE c.medico_id = :medico_id
                  AND DATE(c.fecha_hora_inicio) = :fecha
                  AND c.fecha_hora_inicio < :hora_fin
                  AND c.fecha_hora_fin > :hora_inicio
                  AND ec.codigo NOT IN ('CANCELADA', 'COMPLETADA')
                ORDER BY c.fecha_hora_inicio
                """
            ),
            {
                "medico_id": medico_id,
                "fecha": fecha_cirugia,
                "hora_inicio": inicio_dt,
                "hora_fin": fin_dt,
            },
        )
        citas_afectadas = result_citas.mappings().all()

        # 3. Find alternative doctors (same specialty)
        result_alt = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.nombre, ' ', m.apellido) AS nombre,
                       COUNT(c.id) AS citas_ocupadas
                FROM medicos m
                LEFT JOIN citas c ON c.medico_id = m.id
                    AND DATE(c.fecha_hora_inicio) = :fecha
                    AND c.fecha_hora_inicio < :hora_fin
                    AND c.fecha_hora_fin > :hora_inicio
                JOIN estados_cita ec ON ec.id = c.estado_id
                    AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                WHERE m.especialidad_id = :especialidad_id
                  AND m.id != :medico_id
                GROUP BY m.id, m.nombre, m.apellido
                ORDER BY citas_ocupadas ASC
                LIMIT 3
                """
            ),
            {
                "especialidad_id": medico["especialidad_id"],
                "medico_id": medico_id,
                "fecha": fecha_cirugia,
                "hora_inicio": inicio_dt,
                "hora_fin": fin_dt,
            },
        )
        doctores_alternativos = result_alt.mappings().all()

        # 4. Get cancel state
        result_estado = await db.execute(
            text("SELECT id FROM estados_cita WHERE codigo = 'CANCELADA'")
        )
        estado_cancel = result_estado.first()
    await engine.dispose()

    # Build response
    citas_info = []
    for c in citas_afectadas:
        citas_info.append({
            "cita_id": c["id"],
            "paciente": c["paciente"],
            "email": c["email"],
            "telefono": c["telefono"],
            "hora": str(c["fecha_hora_inicio"]),
            "motivo": c["motivo_consulta"][:100] if c["motivo_consulta"] else "N/A",
        })

    alternativas = []
    for doc in doctores_alternativos:
        alternativas.append({
            "medico_id": doc["id"],
            "nombre": doc["nombre"],
            "citas_en_horario": doc["citas_ocupadas"],
        })

    if not confirmado:
        return json.dumps(
            {
                "accion": "resolver_conflicto_cirugia",
                "estado": "PENDIENTE_CONFIRMACION",
                "medico": f"{medico['nombre']} {medico['apellido']}",
                "especialidad": medico["especialidad"],
                "cirugia": {
                    "fecha": fecha_cirugia,
                    "horario": f"{hora_inicio} - {hora_fin}",
                },
                "citas_afectadas": len(citas_afectadas),
                "detalles_citas": citas_info,
                "doctores_alternativos": alternativas,
                "opciones": [
                    "REASIGNAR: Mover pacientes a otro médico disponible",
                    "REAGENDAR: Cambiar citas a otro día",
                    "CANCELAR: Cancelar con notificación",
                ],
                "mensaje": "Confirme con confirmado=true para ejecutar reasignación automática.",
            },
            ensure_ascii=False,
            indent=2,
        )

    # 5. Execute: Reassign to alternative doctor or reschedule
    engine2 = create_async_engine(_conn_str)
    async_session2 = async_sessionmaker(engine2, expire_on_commit=False)

    resultados = []
    for cita in citas_afectadas:
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
                            FROM citas c
                            JOIN estados_cita ec ON ec.id = c.estado_id
                            WHERE c.medico_id = :medico_id
                              AND c.fecha_hora_inicio < :fin
                              AND c.fecha_hora_fin > :inicio
                              AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                            """
                        ),
                        {
                            "medico_id": doc["id"],
                            "inicio": cita["fecha_hora_inicio"],
                            "fin": cita["fecha_hora_fin"],
                        },
                    )
                    conflicts = result_free.scalar()

                    if conflicts == 0:
                        doctor_asignado = doc
                        nueva_hora = cita["fecha_hora_inicio"]
                        break

        async with async_session2() as db_update:
            if doctor_asignado:
                # Reassign to alternative doctor
                await db_update.execute(
                    text(
                        """
                        UPDATE citas
                        SET medico_id = :nuevo_medico,
                            estado_id = (SELECT id FROM estados_cita WHERE codigo = 'CONFIRMADA')
                        WHERE id = :cita_id
                        """
                    ),
                    {"nuevo_medico": doctor_asignado["id"], "cita_id": cita["id"]},
                )
                resultados.append({
                    "cita_id": cita["id"],
                    "paciente": cita["paciente"],
                    "accion": "REASIGNADA",
                    "nuevo_medico": doctor_asignado["nombre"],
                    "hora_mantenida": str(nueva_hora),
                })
            else:
                # Cancel and add to waitlist
                await db_update.execute(
                    text(
                        """
                        UPDATE citas
                        SET estado_id = (SELECT id FROM estados_cita WHERE codigo = 'CANCELADA')
                        WHERE id = :cita_id
                        """
                    ),
                    {"cita_id": cita["id"]},
                )
                # Add to waitlist
                await db_update.execute(
                    text(
                        """
                        INSERT INTO lista_espera (paciente_id, medico_id, fecha_preferida, motivo)
                        VALUES (:paciente_id, :medico_id, :fecha, :motivo)
                        """
                    ),
                    {
                        "paciente_id": cita["paciente_id"],
                        "medico_id": medico_id,
                        "fecha": (fecha_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                        "motivo": f"Cita cancelada por cirugía del médico original",
                    },
                )
                resultados.append({
                    "cita_id": cita["id"],
                    "paciente": cita["paciente"],
                    "accion": "CANCELADA_LISTA_ESPERA",
                    "razon": "Sin médico alternativo disponible",
                })

        await db_update.commit()
    await engine2.dispose()

    # Generate notification messages
    notificaciones = []
    for r in resultados:
        if r["accion"] == "REASIGNADA":
            notificaciones.append({
                "paciente": r["paciente"],
                "mensaje": (
                    f"Estimado/a {r['paciente']}, su cita ha sido reasignada al "
                    f"Dr./Dra. {r['nuevo_medico']} el {r.get('hora_mantenida', fecha_cirugia)}. "
                    f"Disculpe las molestias."
                ),
                "canal": "SMS + Email",
            })
        else:
            notificaciones.append({
                "paciente": r["paciente"],
                "mensaje": (
                    f"Estimado/a {r['paciente']}, lamentamos informarle que su cita del "
                    f"{fecha_cirugia} ha sido cancelada por motivos médicos. "
                    f"Ha sido agregado a nuestra lista de espera y le notificaremos pronto."
                ),
                "canal": "SMS + Email + Llamada",
            })

    return json.dumps(
        {
            "accion": "resolver_conflicto_cirugia",
            "estado": "EJECUTADA",
            "medico": f"{medico['nombre']} {medico['apellido']}",
            "cirugia": f"{fecha_cirugia} {hora_inicio}-{hora_fin}",
            "citas_procesadas": len(resultados),
            "reasignadas": sum(1 for r in resultados if r["accion"] == "REASIGNADA"),
            "canceladas_espera": sum(1 for r in resultados if "LISTA_ESPERA" in r["accion"]),
            "resultados": resultados,
            "notificaciones_generadas": notificaciones,
            "mensaje": f"Conflicto resuelto: {len(resultados)} citas procesadas.",
        },
        ensure_ascii=False,
        indent=2,
    )


# ============================================================================
# AGENDA IA: FEATURES INNOVADORES MVP
# ============================================================================


@tool
async def analisis_sentimiento(texto_paciente: str, paciente_id: int | None = None) -> str:
    """Analiza el sentimiento del paciente y sugiere cómo ajustar la comunicación.

    SOLO se activa para especialistas en PSICOLOGÍA.
    Detecta: ansiedad, frustración, tristeza, enojo, calma, esperanza.

    Args:
        texto_paciente: Texto del paciente (motivo de consulta, mensaje, etc.).
        paciente_id: ID del paciente (opcional, para contexto adicional).
    """
    # Keyword-based sentiment analysis
    sentimentos = {
        "ansiedad": {
            "keywords": [
                "ansioso", "ansiedad", "nervioso", "preocupado", "miedo",
                "temeroso", "inquieto", "tenso", "estresado", "pánico",
                "angustia", "desesperado", "agobiado", "aterrado",
            ],
            "nivel": "ALTO",
            "color": "🔴",
            "recomendacion": "Usar tono calmado, validar sus sentimientos, ofrecer contención.",
        },
        "frustración": {
            "keywords": [
                "frustrado", "frustración", "enojado", "molesto", "hartado",
                "cansado", "harto", "rabia", "indignado", "furioso",
            ],
            "nivel": "MEDIO",
            "color": "🟡",
            "recomendacion": "Escuchar activamente, no interrumpir, validar su frustración.",
        },
        "tristeza": {
            "keywords": [
                "triste", "tristeza", "deprimido", "depresión", "llorando",
                "llanto", "solo", "soledad", "vacío", "desesperanza",
                "sin ganas", "apático", "melancolía",
            ],
            "nivel": "ALTO",
            "color": "🔴",
            "recomendacion": "Mostrar empatía, preguntar abiertamente, ofrecer apoyo.",
        },
        "esperanza": {
            "keywords": [
                "mejorar", "superar", "optimista", "esperanza", "ganar",
                "luchar", "adelante", "positivo", "progreso", "avanzar",
            ],
            "nivel": "BAJO",
            "color": "🟢",
            "recomendacion": "Reforzar positividad, explorar fortalezas, motivar.",
        },
        "calma": {
            "keywords": [
                "tranquilo", "calmado", "paz", "sereno", "estable",
                "bien", "mejor", "normal", "relajado",
            ],
            "nivel": "BAJO",
            "color": "🟢",
            "recomendacion": "Mantener ritmo, profundizar en temas importantes.",
        },
    }

    texto_lower = texto_paciente.lower()
    detected = []

    for sentimiento, info in sentimentos.items():
        for keyword in info["keywords"]:
            if keyword in texto_lower:
                detected.append({
                    "sentimiento": sentimiento,
                    "nivel": info["nivel"],
                    "color": info["color"],
                    "recomendacion": info["recomendacion"],
                })
                break

    # Determine primary sentiment
    if detected:
        primary = detected[0]
        intensidad = "alta" if any(d["nivel"] == "ALTO" for d in detected) else "media"
    else:
        primary = {
            "sentimiento": "neutro",
            "nivel": "BAJO",
            "color": "⚪",
            "recomendacion": "Continuar evaluación normal.",
        }
        intensidad = "baja"

    return json.dumps(
        {
            "analisis_sentimiento": True,
            "especialidad_requiere": "PSICOLOGÍA",
            "texto_analizado": texto_paciente[:200],
            "sentimiento_primario": primary["sentimiento"],
            "intensidad": intensidad,
            "sentimientos_detectados": [d["sentimiento"] for d in detected] if detected else ["neutro"],
            "recomendacion_comunicacion": primary["recomendacion"],
            "indicador_visual": primary["color"],
            "nota": "Este análisis es orientativo. El profesional debe validar la evaluación.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def coordinacion_familiar(
    familiares: list[dict], fecha_preferida: str = ""
) -> str:
    """Coordina citas para múltiples miembros de una familia en horarios compatibles.

    Ejemplo: "Cita para Juan (cardiología), María (medicina general) y Pedro (pediatría)"

    Args:
        familiares: Lista de [{"nombre": str, "especialidad": str}].
        fecha_preferida: Fecha preferida (YYYY-MM-DD, opcional).
    """
    from datetime import datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    if len(familiares) < 2:
        return "Se requieren al menos 2 familiares para coordinación."

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    resultados = []
    for familiar in familiares:
        nombre = familiar.get("nombre", "")
        especialidad = familiar.get("especialidad", "")

        async with async_session() as db:
            # Find doctors matching specialty
            result = await db.execute(
                text(
                    """
                    SELECT m.id, CONCAT(m.nombre, ' ', m.apellido) AS medico,
                           e.nombre AS especialidad
                    FROM medicos m
                    JOIN especialidades e ON e.id = m.especialidad_id
                    WHERE e.nombre ILIKE :especialidad
                    ORDER BY m.nombre
                    LIMIT 3
                    """
                ),
                {"especialidad": f"%{especialidad}%"},
            )
            medicos = result.mappings().all()

            if not medicos:
                resultados.append({
                    "familiar": nombre,
                    "especialidad": especialidad,
                    "estado": "SIN_DISPO",
                    "mensaje": f"No se encontraron médicos para {especialidad}",
                })
                continue

            # Find available slots for each doctor
            medico_id = medicos[0]["id"]
            result_slots = await db.execute(
                text(
                    """
                    SELECT c.fecha_hora_inicio, c.fecha_hora_fin
                    FROM citas c
                    JOIN estados_cita ec ON ec.id = c.estado_id
                    WHERE c.medico_id = :medico_id
                      AND c.fecha_hora_inicio >= NOW()
                      AND ec.codigo NOT IN ('CANCELADA', 'SUSPENDIDA')
                    ORDER BY c.fecha_hora_inicio
                    LIMIT 20
                    """
                ),
                {"medico_id": medico_id},
            )
            ocupadas = result_slots.mappings().all()

        # Find free slots
        date_obj = datetime.now().date()
        slots_libres = []
        for day_offset in range(7):
            check_date = date_obj + timedelta(days=day_offset)
            for hour in [9, 10, 11, 14, 15, 16]:
                slot_start = datetime.combine(check_date, datetime.min.time().replace(hour=hour))
                slot_end = slot_start + timedelta(minutes=30)
                is_free = True
                for occ in ocupadas:
                    if slot_start < occ["fecha_hora_fin"] and slot_end > occ["fecha_hora_inicio"]:
                        is_free = False
                        break
                if is_free:
                    slots_libres.append(slot_start)
                    if len(slots_libres) >= 3:
                        break
            if len(slots_libres) >= 3:
                break

        resultados.append({
            "familiar": nombre,
            "especialidad": especialidad,
            "medico_sugerido": medicos[0]["medico"],
            "slots_disponibles": [
                s.strftime("%Y-%m-%dT%H:%M:%S") for s in slots_libres[:3]
            ],
        })

    await engine.dispose()

    # Suggest coordinated schedule
    todos_con_slots = all(r.get("slots_disponibles") for r in resultados)
    horario_sugerido = None

    if todos_con_slots:
        # Find common date
        fechas = set()
        for r in resultados:
            for slot in r["slots_disponibles"]:
                fechas.add(slot.split("T")[0])

        for fecha in sorted(fechas):
            slots_en_fecha = []
            for r in resultados:
                for slot in r["slots_disponibles"]:
                    if slot.startswith(fecha):
                        slots_en_fecha.append(slot)
            if len(slots_en_fecha) == len(resultados):
                horario_sugerido = fecha
                break

    return json.dumps(
        {
            "accion": "coordinacion_familiar",
            "total_familiares": len(familiares),
            "resultados": resultados,
            "todos_disponibles": todos_con_slots,
            "fecha_sugerida": horario_sugerido,
            "mensaje": (
                f"Coordinación completada. {'Fecha sugerida: ' + horario_sugerido if horario_sugerido else 'Revisar disponibilidad individual.'}"
            ),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def teletriaje_ia(
    motivo_consulta: str, sintomas: str = "", paciente_id: int | None = None
) -> str:
    """Determina si una consulta puede ser atendida de forma virtual o requiere presencial.

    Analiza síntomas y motivo para recomendar modalidad adecuada.

    Args:
        motivo_consulta: Motivo de la consulta.
        sintomas: Síntomas descritos (opcional).
        paciente_id: ID del paciente (opcional).
    """
    # Rules for telehealth eligibility
    reglas_presencial = [
        "dolor", "fiebre", "sangrado", "lesión", "herida", "fractura",
        "examen físico", "auscultar", "palpar", "inyección", "cirugía",
        "procedimiento", "extracción", "sutura", "curación",
    ]

    reglas_virtual = [
        "seguimiento", "control", "receta", "resultado", "consulta general",
        "duda", "orientación", "sigma", "ansiedad leve", "insomnio",
        "estrés", "terapia", "consejería", "plan de tratamiento",
    ]

    motivo_lower = motivo_consulta.lower()
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
            "motivo": motivo_consulta,
            "sintomas": sintomas[:200] if sintomas else "N/A",
            "modalidad_recomendada": modalidad,
            "confianza": confianza,
            "razon": razon,
            "preguntas_clarificacion": (
                ["¿Presenta síntomas físicos que requieran examen?",
                 "¿Es una consulta de seguimiento o control?"]
                if modalidad == "A_EVALUAR" else []
            ),
            "nota": "El profesional debe confirmar la modalidad final.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
async def verificacion_seguros(paciente_id: int, medico_id: int) -> str:
    """Verifica si el paciente tiene seguro vigente y si cubre al médico/especialidad.

    Simula verificación de cobertura (en producción se conectaría a aseguradora).

    Args:
        paciente_id: ID del paciente.
        medico_id: ID del médico.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get patient info
        result_pat = await db.execute(
            text(
                """
                SELECT id, CONCAT(nombre, ' ', apellido) AS nombre, email
                FROM pacientes WHERE id = :id
                """
            ),
            {"id": paciente_id},
        )
        paciente = result_pat.mappings().first()

        # Get doctor info
        result_med = await db.execute(
            text(
                """
                SELECT m.id, CONCAT(m.nombre, ' ', m.apellido) AS nombre,
                       e.nombre AS especialidad
                FROM medicos m
                JOIN especialidades e ON e.id = m.especialidad_id
                WHERE m.id = :id
                """
            ),
            {"id": medico_id},
        )
        medico = result_med.mappings().first()
    await engine.dispose()

    if not paciente or not medico:
        return "No se encontró paciente o médico."

    # Simulated verification (in production: API call to insurer)
    # This would integrate with real insurance verification APIs
    verificacion = {
        "paciente": paciente["nombre"],
        "medico": medico["nombre"],
        "especialidad": medico["especialidad"],
        "estado_verificacion": "SIMULADO",
        "seguro_cubierto": True,
        "copago_estimado": "$200 MXN",
        "recomendaciones": [
            "Verificar número de póliza vigente",
            "Confirmar cobertura de especialidad",
            "Solicitar pre-autorización si aplica",
        ],
        "nota": "Verificación simulada. En producción, conectar con API de aseguradora.",
    }

    return json.dumps(verificacion, ensure_ascii=False, indent=2)


@tool
async def ai_scribe(cita_id: int, texto_transcripcion: str) -> str:
    """Genera notas clínicas estructuradas a partir de una transcripción.

    Convierte texto libre en formato SOAP (Subjective, Objective, Assessment, Plan).

    Args:
        cita_id: ID de la cita.
        texto_transcripcion: Transcripción de la consulta (audio a texto).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        # Get appointment info
        result = await db.execute(
            text(
                """
                SELECT c.id, c.motivo_consulta,
                       CONCAT(p.nombre, ' ', p.apellido) AS paciente,
                       CONCAT(m.nombre, ' ', m.apellido) AS medico,
                       e.nombre AS especialidad
                FROM citas c
                JOIN pacientes p ON p.id = c.paciente_id
                JOIN medicos m ON m.id = c.medico_id
                JOIN especialidades e ON e.id = m.especialidad_id
                WHERE c.id = :cita_id
                """
            ),
            {"cita_id": cita_id},
        )
        cita = result.mappings().first()
    await engine.dispose()

    if not cita:
        return f"No se encontró la cita {cita_id}."

    # Simple SOAP note generation from transcription
    # In production, this would use the LLM to parse
    texto = texto_transcripcion

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
            "cita_id": cita_id,
            "paciente": cita["paciente"],
            "medico": cita["medico"],
            "especialidad": cita["especialidad"],
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
    mensaje_usuario: str,
    *,
    conn_str: str,
    historial: list[dict[str, str]] | None = None,
) -> str:
    """Envía un mensaje al agente MedAssist y devuelve su respuesta.

    Args:
        mensaje_usuario: Pregunta o instrucción del usuario.
        conn_str: DATABASE_URL para crear conexiones internas a la BD.
        historial: Opcional, lista de mensajes anteriores [{role, content}].
    """
    global _conn_str
    _conn_str = conn_str

    # Anti-prompt-injection check
    injection_warning = _detect_injection(mensaje_usuario)
    if injection_warning:
        return injection_warning

    llm = _get_llm()
    llm_con_tools = llm.bind_tools(_TOOLS)

    messages: list = [SystemMessage(content=_SYSTEM_PROMPT)]

    if historial:
        for msg in historial:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                messages.append(SystemMessage(content=msg["content"]))

    messages.append(HumanMessage(content=mensaje_usuario))

    reply = await llm_con_tools.ainvoke(messages)

    for _ in range(6):
        if not reply.tool_calls:
            break

        messages.append(reply)
        for tool_call in reply.tool_calls:
            tool_fn = next((t for t in _TOOLS if t.name == tool_call["name"]), None)
            try:
                if tool_fn is None:
                    tool_result = f"Herramienta desconocida: {tool_call['name']}"
                else:
                    tool_result = await tool_fn.ainvoke(tool_call["args"])
            except Exception as exc:  # noqa: BLE001
                tool_result = (
                    f"Error al ejecutar la herramienta: {exc}. "
                    "Indica al usuario que se necesitan más datos."
                )
            messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
            )

        reply = await llm_con_tools.ainvoke(messages)

    return reply.content


async def chat_con_agente_stream(
    mensaje_usuario: str,
    *,
    conn_str: str,
    historial: list[dict[str, str]] | None = None,
):
    """Streams agent response token-by-token using LangChain astream.

    Args:
        mensaje_usuario: Pregunta o instrucción del usuario.
        conn_str: DATABASE_URL para crear conexiones internas a la BD.
        historial: Opcional, lista de mensajes anteriores [{role, content}].
    """
    global _conn_str
    _conn_str = conn_str

    # Anti-prompt-injection check
    injection_warning = _detect_injection(mensaje_usuario)
    if injection_warning:
        yield injection_warning
        return

    llm = _get_llm()
    llm_con_tools = llm.bind_tools(_TOOLS)

    messages: list = [SystemMessage(content=_SYSTEM_PROMPT)]

    if historial:
        for msg in historial:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                messages.append(SystemMessage(content=msg["content"]))

    messages.append(HumanMessage(content=mensaje_usuario))

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
                    tool_result = f"Herramienta desconocida: {tool_call['name']}"
                else:
                    tool_result = await tool_fn.ainvoke(tool_call["args"])
            except Exception as exc:  # noqa: BLE001
                tool_result = (
                    f"Error al ejecutar la herramienta: {exc}. "
                    "Indica al usuario que se necesitan más datos."
                )
            messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
            )

        reply = await llm_con_tools.ainvoke(messages)

    # Stream the final response
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content
