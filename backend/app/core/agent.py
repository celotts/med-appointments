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
