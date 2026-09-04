"""Agente conversacional RAG + herramientas de agendamiento con LangChain + Ollama."""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

_SYSTEM_PROMPT = """Eres MedAssist, un asistente inteligente de gestión de citas médicas.

Puedes:
1. Responder preguntas sobre el calendario de citas de médicos y pacientes.
2. Buscar en notas médicas y documentos vectoriales usando búsqueda semántica.
3. Ayudar a reagendar o cancelar citas (solo con confirmación del usuario).
4. Resumir información médica de notas clínicas.

Reglas:
- Sé conciso y profesional.
- Si no tienes suficiente información, indica qué dato falta.
- Nunca inventes diagnósticos, tratamientos ni datos médicos.
- Al reagendar, valida que el usuario confirme explícitamente.
- Usa las herramientas disponibles para consultar la base de datos en tiempo real.
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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from core.rag import search_documentos as _search

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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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


_TOOLS = [
    buscar_en_documentos,
    consultar_citas_paciente,
    consultar_citas_medico,
    buscar_pacientes,
    buscar_medicos,
    contar_registros,
    sugerir_reagendamiento,
    ejecutar_reagendamiento,
    cancelar_cita,
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
            tool_fn = next(
                (t for t in _TOOLS if t.name == tool_call["name"]), None
            )
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
