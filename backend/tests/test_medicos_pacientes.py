"""Smoke test integral: login -> CRUD de Médicos y Pacientes contra la BD real.

Uso:
    cd backend
    set -a; . ../.env; set +a
    DATABASE_URL=postgresql+asyncpg://root:fc100711@localhost:5432/appointment \
        python -m tests.test_medicos_pacientes

Requiere el contenedor de Postgres levantado (medical_pgvector).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import models.role  # noqa: F401
import models.user  # noqa: F401
import models.audit  # noqa: F401
import models.specialty  # noqa: F401
import models.medico  # noqa: F401
import models.paciente  # noqa: F401

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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/login/access-token", data=_auth())
        assert r.status_code == 200, f"login {r.status_code} {r.text}"
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("PASS: login OK")

        # Preparar especialidad para el médico
        r = await client.post(
            "/api/v1/specialties/", headers=headers, json={"nombre": "Oncología Smoke"}
        )
        assert r.status_code == 201, r.text
        esp_id = r.json()["id"]

        # ---------- MÉDICOS ----------
        r = await client.post(
            "/api/v1/medicos/",
            headers=headers,
            json={
                "especialidad_id": esp_id,
                "nombre": "Laura",
                "apellido": "Gómez",
                "cedula_profesional": "CP-1000",
                "email": "laura.gomez@med.com",
                "telefono": "555-0100",
            },
        )
        assert r.status_code == 201, f"crear médico {r.status_code} {r.text}"
        med = r.json()
        med_id = med["id"]
        assert med["especialidad_id"] == esp_id
        print(f"PASS: médico creado id={med_id}")

        # Validar FK: especialidad inexistente -> 404
        r = await client.post(
            "/api/v1/medicos/",
            headers=headers,
            json={
                "especialidad_id": 99999,
                "nombre": "X",
                "apellido": "Y",
                "cedula_profesional": "CP-X1",
                "email": "x@med.com",
            },
        )
        assert r.status_code == 404, f"esperaba 404, obtuve {r.status_code}"
        print("PASS: médico con especialidad inexistente -> 404")

        # Listar y filtrar por especialidad
        r = await client.get(
            f"/api/v1/medicos/?especialidad_id={esp_id}", headers=headers
        )
        assert r.status_code == 200
        assert any(m["id"] == med_id for m in r.json())
        print("PASS: médicos listados y filtrados por especialidad")

        # Actualizar
        r = await client.put(
            f"/api/v1/medicos/{med_id}",
            headers=headers,
            json={"telefono": "555-0199", "apellido": "Gómez R."},
        )
        assert r.status_code == 200 and r.json()["telefono"] == "555-0199"
        print("PASS: médico actualizado")

        # ---------- PACIENTES ----------
        r = await client.post(
            "/api/v1/pacientes/",
            headers=headers,
            json={
                "nombre": "Carlos",
                "apellido": "Ruiz",
                "fecha_nacimiento": "1985-04-12",
                "email": "carlos.ruiz@mail.com",
                "telefono": "555-0200",
            },
        )
        assert r.status_code == 201, f"crear paciente {r.status_code} {r.text}"
        pac = r.json()
        pac_id = pac["id"]
        print(f"PASS: paciente creado id={pac_id}")

        # Email duplicado -> 400
        r = await client.post(
            "/api/v1/pacientes/",
            headers=headers,
            json={
                "nombre": "Carlos",
                "apellido": "Otro",
                "fecha_nacimiento": "1980-01-01",
                "email": "carlos.ruiz@mail.com",
                "telefono": "555-0201",
            },
        )
        assert r.status_code == 400, f"esperaba 400, obtuve {r.status_code}"
        print("PASS: paciente con email duplicado -> 400")

        # Listar
        r = await client.get("/api/v1/pacientes/", headers=headers)
        assert r.status_code == 200 and any(p["id"] == pac_id for p in r.json())
        print("PASS: pacientes listados")

        # Obtener por id
        r = await client.get(f"/api/v1/pacientes/{pac_id}", headers=headers)
        assert r.status_code == 200 and r.json()["id"] == pac_id
        print("PASS: paciente obtenido por id")

        # Limpieza
        r = await client.delete(f"/api/v1/medicos/{med_id}", headers=headers)
        assert r.status_code == 200
        r = await client.delete(f"/api/v1/pacientes/{pac_id}", headers=headers)
        assert r.status_code == 200
        r = await client.delete(f"/api/v1/specialties/{esp_id}", headers=headers)
        assert r.status_code == 200
        print("PASS: limpieza de datos de prueba")

    print("\nTESTS MÉDICOS Y PACIENTES OK ✅")


async def test_integration():
    await main()


if __name__ == "__main__":
    asyncio.run(main())
