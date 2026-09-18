from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(__file__).resolve().parent

_DEFAULTS: dict[str, Any] = {
    "name": "MedAppointments MCP",
    "title": "MedAppointments MCP Server",
    "description": "Herramientas de agenda para citas médicas.",
    "instructions": "Usa estas herramientas para leer o modificar citas y evaluar disponibilidad de doctores.",
    "transport": "stdio",
    "host": "127.0.0.1",
    "port": 8765,
    "log_level": "INFO",
    "database_url": None,
    "tools": {},
}

# (variable de entorno, clave en config)
_ENV_MAP: list[tuple[str, str]] = [
    ("MCP_TRANSPORT", "transport"),
    ("MCP_HOST", "host"),
    ("MCP_PORT", "port"),
    ("MCP_LOG_LEVEL", "log_level"),
    ("MCP_DATABASE_URL", "database_url"),
    ("MCP_NAME", "name"),
]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _load_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: str | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Construye la config del servidor MCP con esta precedencia (menor a mayor):
      1. Valores por defecto.
      2. Archivo mcp_server/config.json (o el indicado por MCP_CONFIG).
      3. Variables de entorno MCP_*.
      4. tools adicionales via MCP_TOOLS (JSON) para activar grupos sin editar código.
    """
    env = env if env is not None else os.environ

    config = deepcopy(_DEFAULTS)
    file_path = Path(env.get("MCP_CONFIG", path or "")) if (path or env.get("MCP_CONFIG")) else (_CONFIG_DIR / "config.json")
    if file_path.exists():
        _deep_merge(config, _load_file(file_path))

    for var, key in _ENV_MAP:
        if var in env and env[var] != "":
            config[key] = env[var]

    if raw := env.get("MCP_TOOLS"):
        try:
            _deep_merge(config["tools"], json.loads(raw))
        except json.JSONDecodeError:
            raise ValueError("MCP_TOOLS no es un JSON valido")

    return config