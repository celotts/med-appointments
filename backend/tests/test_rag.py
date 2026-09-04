"""Smoke test integral: RAG + AI Agent contra la BD real + Ollama local.

Uso:
    cd backend
    set -a; . ../.env; set +a
    DATABASE_URL=postgresql+asyncpg://root:fc100711@localhost:5432/appointment \
        python -m tests.test_rag

Requiere: contenedor medical_pgvector + Ollama corriendo con nomic-embed-text y llama3.2.
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import models.role  # noqa: F401
import models.user  # noqa: F401
import models.audit  # noqa: F401
import models.specialty  # noqa: F401
import models.medico  # noqa: F401
import models.paciente  # noqa: F401
import models.estado_cita  # noqa: F401
import models.cita  # noqa: F401
import models.nota_medica  # noqa: F401

from httpx import ASGITransport, AsyncClient

from main import app
from initial_data import main as bootstrap_initial_data


def _auth() -> dict:
    return {
        "username": os.environ["FIRST_SUPERUSER_EMAIL"],
        "password": os.environ["FIRST_SUPERUSER_PASSWORD"],
    }


async def main() -> None:
    await bootstrap_initial_data()

    suf = int(time.time())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=120) as client:
        r = await client.post("/api/v1/login/access-token", data=_auth())
        assert r.status_code == 200, r.text
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        print("PASS: login OK")

        # --- Health check ---
        r = await client.get("/api/v1/rag/health", headers=headers)
        assert r.status_code == 200
        health = r.json()
        assert health["ollama"] == "ok", f"Ollama no accesible: {health}"
        assert health["embedding_model"] == "nomic-embed-text"
        print(f"PASS: RAG health OK (vectors={health['vector_count']})")

        # --- Ingesta manual de documento ---
        r = await client.post(
            "/api/v1/rag/ingest",
            headers=headers,
            json={
                "ref_tipo": "DOCUMENTO",
                "titulo": f"Guía de hipertensión arterial {suf}",
                "contenido": (
                    "La hipertensión arterial se define como presión arterial sistólica "
                    "≥140 mmHg o diastólica ≥90 mmHg. El tratamiento incluye modificaciones "
                    "del estilo de vida y farmacoterapia con IECA, ARA, calcioantagonistas "
                    "o diuréticos tiazídicos."
                ),
            },
        )
        assert r.status_code == 201, r.text
        print("PASS: documento ingestado")

        # --- Búsqueda por similitud semántica ---
        r = await client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={"query": "tratamiento para presión alta", "k": 3},
        )
        assert r.status_code == 200
        results = r.json()
        assert len(results) > 0, "No se encontraron resultados por similitud"
        assert results[0]["similarity"] > 0.3, f"Similitud demasiado baja: {results[0]['similarity']}"
        print(f"PASS: búsqueda semántica OK (top similarity={results[0]['similarity']})")

        # --- Crear cita + nota médica + ingestar al vector store ---
        r = await client.post(
            "/api/v1/specialties/", headers=headers, json={"nombre": f"Neurología RAG {suf}"}
        )
        esp = r.json()["id"]
        r = await client.post(
            "/api/v1/medicos/",
            headers=headers,
            json={
                "especialidad_id": esp,
                "nombre": "Carlos",
                "apellido": "Méndez",
                "cedula_profesional": f"CP-RAG-{suf}",
                "email": f"carlos.mendez.{suf}@med.com",
                "telefono": "555-0500",
            },
        )
        med = r.json()["id"]
        r = await client.post(
            "/api/v1/pacientes/",
            headers=headers,
            json={
                "nombre": "Lucía",
                "apellido": "Fernández",
                "fecha_nacimiento": "1988-03-15",
                "email": f"lucia.fernandez.{suf}@mail.com",
                "telefono": "555-0600",
            },
        )
        pac = r.json()["id"]

        r = await client.post(
            "/api/v1/citas/",
            headers=headers,
            json={
                "paciente_id": pac,
                "medico_id": med,
                "fecha_hora_inicio": "2026-09-12T11:00:00Z",
                "fecha_hora_fin": "2026-09-12T11:30:00Z",
                "motivo_consulta": "Dolor de cabeza recurrente",
            },
        )
        assert r.status_code == 201, r.text
        cita_id = r.json()["id"]

        r = await client.post(
            "/api/v1/notas/",
            headers=headers,
            json={
                "cita_id": cita_id,
                "diagnostico": "Cefalea tensional crónica",
                "tratamiento": "Ibuprofeno 400mg cada 8h, fisioterapia cervical",
                "observaciones": "Seguimiento en 2 semanas",
            },
        )
        assert r.status_code == 201, r.text

        r = await client.post(
            f"/api/v1/rag/ingest-nota/{cita_id}",
            headers=headers,
        )
        assert r.status_code == 201, r.text
        print("PASS: nota médica ingestada al vector store")

        # --- Buscar la nota por similitud ---
        r = await client.post(
            "/api/v1/rag/search",
            headers=headers,
            json={
                "query": "cefalea y dolor de cabeza",
                "ref_tipo": "NOTA_MEDICA",
                "k": 3,
            },
        )
        assert r.status_code == 200
        results = r.json()
        assert any(
            "Cefalea" in res["contenido"] for res in results
        ), f"No se encontró la nota por similitud: {results}"
        print("PASS: búsqueda de nota médica por similitud OK")

        # --- Conversar con el agente ---
        r = await client.post(
            "/api/v1/rag/chat",
            headers=headers,
            json={"message": "¿Cuáles son las citas del médico Carlos Méndez?"},
        )
        assert r.status_code == 200, f"Error del agente: {r.status_code} {r.text}"
        respuesta = r.json()["respuesta"]
        assert len(respuesta) > 0, "Respuesta vacía del agente"
        print(f"PASS: agente responde ({len(respuesta)} chars)")

        # --- Herramientas de EJECUCIÓN del agente (reagendar/cancelar con confirmación) ---
        import core.agent as agent_mod

        agent_mod._conn_str = os.environ["DATABASE_URL"]

        # Segunda cita para herramienta de ejecución
        r = await client.post(
            "/api/v1/citas/",
            headers=headers,
            json={
                "paciente_id": pac,
                "medico_id": med,
                "fecha_hora_inicio": "2026-09-13T12:00:00Z",
                "fecha_hora_fin": "2026-09-13T12:30:00Z",
                "motivo_consulta": "Control anual",
            },
        )
        assert r.status_code == 201, r.text
        cita_ejec_id = r.json()["id"]

        # Reagendar sin confirmación -> no ejecuta
        msg = await agent_mod.ejecutar_reagendamiento.ainvoke(
            {"cita_id": cita_ejec_id, "nueva_fecha": "2026-09-20T10:00:00Z", "confirmado": False}
        )
        assert "confirmaci" in msg.lower(), msg
        # Reagendar con confirmación -> ejecuta y pasa a REAGENDADA
        msg = await agent_mod.ejecutar_reagendamiento.ainvoke(
            {"cita_id": cita_ejec_id, "nueva_fecha": "2026-09-20T10:00:00Z", "confirmado": True}
        )
        assert "reagendada" in msg.lower(), msg
        # Verificar estado en BD
        r = await client.get(f"/api/v1/citas/{cita_ejec_id}", headers=headers)
        assert r.json()["estado"]["codigo"] == "REAGENDADA"
        print("PASS: agente reagenda con confirmación (REAGENDADA)")

        # Cancelar con confirmación -> CANCELADA
        msg = await agent_mod.cancelar_cita.ainvoke({"cita_id": cita_ejec_id, "confirmado": True})
        assert "cancelada" in msg.lower(), msg
        r = await client.get(f"/api/v1/citas/{cita_ejec_id}", headers=headers)
        assert r.json()["estado"]["codigo"] == "CANCELADA"
        # Reintento de cancelar (terminal) -> rechaza
        msg = await agent_mod.cancelar_cita.ainvoke({"cita_id": cita_ejec_id, "confirmado": True})
        assert "inválida" in msg.lower(), msg
        print("PASS: agente cancela con confirmación + transición terminal validada")

        # Limpieza de la cita de ejecución
        await client.delete(f"/api/v1/citas/{cita_ejec_id}", headers=headers)

        # --- Limpieza de registros entidades ---
        await client.delete(f"/api/v1/citas/{cita_id}", headers=headers)
        await client.delete(f"/api/v1/medicos/{med}", headers=headers)
        await client.delete(f"/api/v1/pacientes/{pac}", headers=headers)
        await client.delete(f"/api/v1/specialties/{esp}", headers=headers)

        # --- Limpieza de documentos vectoriales de prueba (conexión asyncpg propia) ---
        import asyncpg

        dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(
                "DELETE FROM documentos_vectoriales WHERE "
                "titulo LIKE $1 OR titulo LIKE $2",
                f"%{suf}%",
                "Nota médica%",
            )
        finally:
            await conn.close()
        print("PASS: limpieza")

    print("\nTESTS RAG + AI AGENT OK ✅")


async def test_integration():
    await main()


if __name__ == "__main__":
    asyncio.run(main())
