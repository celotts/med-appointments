"""Smoke test integral: login -> CRUD de Especialidades contra la BD real.

Uso:
    cd backend
    set -a; . ../.env; set +a
    DATABASE_URL=postgresql+asyncpg://root:fc100711@localhost:5432/appointment \
        python -m tests.test_specialties

Requiere el contenedor de Postgres levantado (medical_pgvector).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import models.role  # noqa: F401  (registro de mappers en orden)
import models.user  # noqa: F401
import models.audit  # noqa: F401
import models.specialty  # noqa: F401

from httpx import ASGITransport, AsyncClient

from main import app
from initial_data import main as bootstrap_initial_data


def _login_payload() -> dict:
    return {
        "username": os.environ["FIRST_SUPERUSER_EMAIL"],
        "password": os.environ["FIRST_SUPERUSER_PASSWORD"],
    }


async def main() -> None:
    # Asegura que exista el primer superusuario (idempotente). En el contenedor
    # lo hace el evento de startup; aquí lo invocamos explícitamente.
    await bootstrap_initial_data()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Obtener token
        r = await client.post("/api/v1/login/access-token", data=_login_payload())
        assert r.status_code == 200, f"login falló: {r.status_code} {r.text}"
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("PASS: login OK (token obtenido)")

        # 2. Crear especialidad
        r = await client.post(
            "/api/v1/specialties/",
            headers=headers,
            json={"nombre": "Cardiología Smoke", "descripcion": "Para pruebas"},
        )
        assert r.status_code == 201, f"crear: {r.status_code} {r.text}"
        spec = r.json()
        spec_id = spec["id"]
        print(f"PASS: especialidad creada id={spec_id} nombre={spec['nombre']}")

        # 3. Listar especialidades
        r = await client.get("/api/v1/specialties/", headers=headers)
        assert r.status_code == 200
        assert any(s["id"] == spec_id for s in r.json()), "no aparece en el listado"
        print("PASS: especialidad listada")

        # 4. Actualizar
        r = await client.put(
            f"/api/v1/specialties/{spec_id}",
            headers=headers,
            json={"nombre": "Cardiología Smoke Update", "descripcion": "Actualizada"},
        )
        assert r.status_code == 200, f"update: {r.status_code} {r.text}"
        assert r.json()["nombre"] == "Cardiología Smoke Update"
        print("PASS: especialidad actualizada")

        # 5. Obtener por id
        r = await client.get(f"/api/v1/specialties/{spec_id}", headers=headers)
        assert r.status_code == 200 and r.json()["id"] == spec_id
        print("PASS: especialidad obtenida por id")

        # 6. Sin token -> 401
        r = await client.get("/api/v1/specialties/")
        assert r.status_code == 401, f"esperaba 401, obtuve {r.status_code}"
        print("PASS: sin token -> 401 (autenticación funciona)")

        # 7. Eliminar (cleanup)
        r = await client.delete(f"/api/v1/specialties/{spec_id}", headers=headers)
        assert r.status_code == 200
        print("PASS: especialidad eliminada")

        # 8. Verificar eliminada
        r = await client.get(f"/api/v1/specialties/{spec_id}", headers=headers)
        assert r.status_code == 404
        print("PASS: especialidad ya no existe (404)")

    print("\nTESTS ESPECIALIDADES OK ✅")


async def test_integration():
    await main()


if __name__ == "__main__":
    asyncio.run(main())
