"""Configuración compartida de pytest.

Añade la carpeta `app` al sys.path y garantiza que las variables de entorno
necesarias estén disponibles para los tests integrales contra la BD real.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
APP_DIR = str(BACKEND_DIR / "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

TESTS_DIR = str(BACKEND_DIR)
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

# DSN por defecto para desarrollo local (puede sobreescribirse con la env)
if "DATABASE_URL" not in os.environ:
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://root:fc100711@localhost:5432/appointment"
    )

# pytest-asyncio en modo "auto" recolecta las funciones async def test_*.
pytest_plugins = []
