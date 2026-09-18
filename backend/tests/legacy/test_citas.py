"""Smoke test integral: flujo completo de citas y notas médicas contra la BD real.

Cubre: agendar -> conflicto de horario (409) -> confirmar -> reagendar ->
completar (máquina de estados) -> nota médica -> limpieza.

Uso:
    cd backend
    set -a; . ../.env; set +a
    DATABASE_URL=postgresql+asyncpg://root:fc100711@localhost:5432/appointment \
        python -m tests.test_citas
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

    # Sufijo único por corrida para ser idempotente si una corrida previa dejó residuos
    suf = int(time.time())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/login/access-token", data=_auth())
        assert r.status_code == 200, r.text
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        print("PASS: login OK")

        # Catálogo de estados (semilla insertada por migración)
        r = await client.get("/api/v1/estados-cita/", headers=headers)
        assert r.status_code == 200
        codigos = {e["codigo"] for e in r.json()}
        assert {"PENDIENTE", "CONFIRMADA", "COMPLETADA", "CANCELADA", "SUSPENDIDA", "REAGENDADA"} <= codigos, codigos
        print(f"PASS: estados de cita OK ({len(codigos)} estados)")

        # --- Datos base ---
        r = await client.post(
            "/api/v1/specialties/",
            headers=headers,
            json={"nombre": f"Cardiología Smoke {suf}"},
        )
        esp = r.json()["id"]
        r = await client.post(
            "/api/v1/medicos/",
            headers=headers,
            json={
                "especialidad_id": esp,
                "nombre": "Ana",
                "apellido": "Pérez",
                "cedula_profesional": f"CP-2000-{suf}",
                "email": f"ana.perez.{suf}@med.com",
                "telefono": "555-0300",
            },
        )
        med = r.json()["id"]
        r = await client.post(
            "/api/v1/pacientes/",
            headers=headers,
            json={
                "nombre": "Marta",
                "apellido": "López",
                "fecha_nacimiento": "1990-07-21",
                "email": f"marta.lopez.{suf}@mail.com",
                "telefono": "555-0400",
            },
        )
        pac = r.json()["id"]

        # --- Agenda primera cita ---
        r = await client.post(
            "/api/v1/citas/",
            headers=headers,
            json={
                "paciente_id": pac,
                "medico_id": med,
                "fecha_hora_inicio": "2026-09-10T09:00:00Z",
                "fecha_hora_fin": "2026-09-10T09:30:00Z",
                "motivo_consulta": "Dolor torácico",
            },
        )
        assert r.status_code == 201, r.text
        cita = r.json()
        cita_id = cita["id"]
        assert cita["estado"]["codigo"] == "PENDIENTE"
        print(f"PASS: cita agendada id={cita_id} en PENDIENTE")

        # --- Conflicto de horario -- mismo médico, franja solapada ---
        r = await client.post(
            "/api/v1/citas/",
            headers=headers,
            json={
                "paciente_id": pac,
                "medico_id": med,
                "fecha_hora_inicio": "2026-09-10T09:15:00Z",
                "fecha_hora_fin": "2026-09-10T09:45:00Z",
                "motivo_consulta": "Otra consulta",
            },
        )
        assert r.status_code == 409, f"esperaba 409 conflicto, obtuve {r.status_code}: {r.text}"
        print("PASS: conflicto de horario detectado -> 409")

        # Otro médico SÍ puede en la misma franja
        r = await client.post(
            "/api/v1/medicos/",
            headers=headers,
            json={
                "especialidad_id": esp,
                "nombre": "Luis",
                "apellido": "Torres",
                "cedula_profesional": f"CP-2001-{suf}",
                "email": f"luis.torres.{suf}@med.com",
                "telefono": "555-0301",
            },
        )
        med2 = r.json()["id"]
        r = await client.post(
            "/api/v1/citas/",
            headers=headers,
            json={
                "paciente_id": pac,
                "medico_id": med2,
                "fecha_hora_inicio": "2026-09-10T09:15:00Z",
                "fecha_hora_fin": "2026-09-10T09:45:00Z",
                "motivo_consulta": "Chequeo",
            },
        )
        assert r.status_code == 201, f"otro médico debía pasar, obtuve {r.status_code}: {r.text}"
        cita2_id = r.json()["id"]
        print("PASS: otro médico sin conflicto -> 201")

        # --- Confirmar primera cita (PENDIENTE -> CONFIRMADA) ---
        r = await client.patch(
            f"/api/v1/citas/{cita_id}/estado",
            headers=headers,
            json={"estado": "CONFIRMADA"},
        )
        assert r.status_code == 200 and r.json()["estado"]["codigo"] == "CONFIRMADA", r.text
        print("PASS: transición PENDIENTE -> CONFIRMADA")

        # --- Transición inválida: PENDIENTE no se puede cancelar... (ya es CONFIRMADA) ---
        # CONFIRMADA no puede ir a PENDIENTE (regresión)
        r = await client.patch(
            f"/api/v1/citas/{cita_id}/estado",
            headers=headers,
            json={"estado": "PENDIENTE"},
        )
        assert r.status_code == 400, f"transición inválida debía dar 400, obtuve {r.status_code}"
        print("PASS: transición inválida CONFIRMADA -> PENDIENTE -> 400")

        # --- Reagendar cita 2 (libera su franja con el médico original) ---
        r = await client.put(
            f"/api/v1/citas/{cita2_id}",
            headers=headers,
            json={
                "fecha_hora_inicio": "2026-09-11T10:00:00Z",
                "fecha_hora_fin": "2026-09-11T10:30:00Z",
                "motivo_consulta": "Chequeo reprogramado",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["estado"]["codigo"] == "REAGENDADA", r.json()["estado"]
        print("PASS: reagendada -> REAGENDADA")

        # Reagendar cita CANCELADA debe fallar
        r = await client.patch(
            f"/api/v1/citas/{cita_id}/estado",
            headers=headers,
            json={"estado": "COMPLETADA"},
        )
        assert r.status_code == 200
        r = await client.put(
            f"/api/v1/citas/{cita_id}",
            headers=headers,
            json={"fecha_hora_inicio": "2026-09-12T09:00:00Z", "fecha_hora_fin": "2026-09-12T09:30:00Z"},
        )
        assert r.status_code == 400, f"reagendar cita completada debía fallar, obtuve {r.status_code}"
        print("PASS: no se puede reagendar cita COMPLETADA -> 400")

        # --- Nota médica ---
        r = await client.post(
            "/api/v1/notas/",
            headers=headers,
            json={
                "cita_id": cita_id,
                "diagnostico": "Tensión arterial elevada",
                "tratamiento": "Ejercicio y dieta baja en sodio",
                "observaciones": "Revisión en 1 mes",
            },
        )
        assert r.status_code == 201, r.text
        nota_id = r.json()["id"]
        print(f"PASS: nota médica creada id={nota_id}")

        # Una sola nota por cita (unique cita_id)
        r = await client.post(
            "/api/v1/notas/",
            headers=headers,
            json={"cita_id": cita_id, "diagnostico": "Duplicado"},
        )
        assert r.status_code == 400, f"nota duplicada debía fallar, obtuve {r.status_code}"
        print("PASS: nota duplicada por cita -> 400")

        # Actualizar nota
        r = await client.put(
            f"/api/v1/notas/{nota_id}",
            headers=headers,
            json={"tratamiento": "Ejercicio, dieta y control mensual"},
        )
        assert r.status_code == 200 and r.json()["tratamiento"].startswith("Ejercicio")
        print("PASS: nota actualizada")

        # --- Limpieza ---
        for n in [f"/api/v1/notas/{nota_id}"]:
            await client.delete(n, headers=headers)
        for c in [f"/api/v1/citas/{cita_id}", f"/api/v1/citas/{cita2_id}"]:
            r = await client.delete(c, headers=headers)
            assert r.status_code == 200
        for m in [f"/api/v1/medicos/{med}", f"/api/v1/medicos/{med2}"]:
            await client.delete(m, headers=headers)
        await client.delete(f"/api/v1/pacientes/{pac}", headers=headers)
        await client.delete(f"/api/v1/specialties/{esp}", headers=headers)
        print("PASS: limpieza de datos de prueba")

    print("\nTESTS CITAS Y NOTAS OK ✅")


async def test_integration():
    await main()


if __name__ == "__main__":
    asyncio.run(main())
