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
2. Búsqueda semántica: buscar en notas médicas y documentos clínicos vectorizados.
3. Análisis de agenda: sugerir horarios óptimos, detectar conflictos, analizar carga de trabajo.
4. Patrones predictivos: analizar comportamiento de pacientes para mejorar asistencia.
5. Resumen de notas clínicas: extraer información relevante de diagnósticos y tratamientos.

HERRAMIENTAS INTELIGENTES DE AGENDA:
- sugerir_horarios_disponibles: Encuentra slots vacíos para un médico en una fecha específica.
- analizar_carga_medico: Muestra estadísticas de ocupación y sugiere días con menor carga.
- detectar_conflictos: Identifica citas superpuestas y propone soluciones.
- analizar_patrones_paciente: Identifica preferencias de días/horarios y tasa de cancelaciones.

REGLAS:
- Sé conciso y profesional.
- Si no tienes suficiente información, indica qué dato falta.
- Nunca inventes diagnósticos, tratamientos ni datos médicos.
- Al reagendar, valida que el usuario confirme explícitamente.
- Usa las herramientas disponibles para consultar la base de datos en tiempo real.
- Para conflictos, siempre sugiere alternativas concretas.
- Al analizar patrones, provide recomendaciones accionables.
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
