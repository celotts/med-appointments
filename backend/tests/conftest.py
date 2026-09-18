"""Fixtures compartidas para los tests de contrato del API.

Diseñado para ejecutarse DENTRO del contenedor `medical_rag_api`
(PYTHONPATH=/app, cwd=/app) mediante `make test`. También funciona desde
el host si se ejecuta con cwd `backend/` y la BD accesible.
"""

import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BACKEND_DIR / "app"
for _p in (str(APP_DIR), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Valores por defecto para ejecución local (en el contenedor ya vienen del entorno)
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:fc100711@localhost:5433/appointment"
)
os.environ.setdefault("FIRST_SUPERUSER_EMAIL", "admin@medapp.com")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "Admin123!")
os.environ.setdefault("SECRET_KEY", "dev-test-secret")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.initial_data import main as bootstrap_initial_data  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


@pytest_asyncio.fixture(scope="session")
async def client():
    """Cliente HTTP que habla con la app vía ASGI, sin servidor externo."""
    await bootstrap_initial_data()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def auth_headers(client):
    response = await client.post(
        "/api/v1/login/access-token",
        data={
            "username": os.environ["FIRST_SUPERUSER_EMAIL"],
            "password": os.environ["FIRST_SUPERUSER_PASSWORD"],
        },
    )
    assert response.status_code == 200, f"login {response.status_code}: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
