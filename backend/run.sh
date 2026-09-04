#!/usr/bin/env bash
#
# Script de arranque y verificación del backend de Medical Appointments RAG API.
#
# Uso:
#   ./run.sh serve          Levanta la API con uvicorn (http://127.0.0.1:8000 por defecto)
#   ./run.sh test           Ejecuta todos los smoke tests contra la BD real (python -m)
#   ./run.sh pytest         Ejecuta los tests con pytest/pytest-asyncio
#   ./run.sh migrate        Aplica las migraciones pendientes de Alembic
#   ./run.sh seeds          Vuelve a aplicar la semilla de estados (idempotente, no usa migración)
#
# Requisitos:
#   - Contenedor de Postgres/pgvector levantado (docker-compose / medical_pgvector)
#   - Ollama corriendo en http://localhost:11434 con nomic-embed-text y llama3.2
#   - Archivo ../.env presente (DATABASE_URL, SECRET_KEY, FIRST_SUPERUSER_*)
#
# Nota: los binarios del venv tienen shebangs rotos; por eso invocamos todo
#       como "venv/bin/python -m <modulo>".
set -euo pipefail

cd "$(dirname "$0")"

PY=venv/bin/python
[ -x "$PY" ] || { echo "ERROR: no encuentro $PY. Crea el venv primero."; exit 1; }

# Cargar variables de entorno del .env raíz
if [ -f ../.env ]; then
  set -a
  . ../.env
  set +a
fi

# Garantizar DSN por defecto para desarrollo local
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://root:fc100711@localhost:5432/appointment}"

APP_DIR=app
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

case "${1:-serve}" in
  serve)
    echo "Arrancando la API en http://$HOST:$PORT ..."
    exec "$PY" -m uvicorn main:app --host "$HOST" --port "$PORT" --app-dir "$APP_DIR"
    ;;
  test)
    shift || true
    if [ "$#" -eq 0 ]; then
      set -- test_specialties test_medicos_pacientes test_citas test_rag
    fi
    for t in "$@"; do
      echo "===== $t ====="
      DATABASE_URL="$DATABASE_URL" "$PY" -m tests.$t
    done
    ;;
  pytest)
    DATABASE_URL="$DATABASE_URL" "$PY" -m pytest -v "$@"
    ;;
  migrate)
    DATABASE_URL="$DATABASE_URL" "$PY" -m alembic upgrade head
    DATABASE_URL="$DATABASE_URL" "$PY" -m alembic current
    ;;
  seeds)
    "$PY" -c "
import sys; sys.path.insert(0, '$APP_DIR')
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ESTADOS = [
    ('PENDIENTE', 'Cita pendiente de confirmación'),
    ('CONFIRMADA', 'Cita confirmada'),
    ('COMPLETADA', 'Cita completada'),
    ('CANCELADA', 'Cita cancelada'),
    ('SUSPENDIDA', 'Cita suspendida'),
    ('REAGENDADA', 'Cita reagendada a nueva fecha'),
]

async def main():
    engine = create_async_engine('$DATABASE_URL')
    async with engine.begin() as conn:
        for cod, desc in ESTADOS:
            await conn.execute(
                text('INSERT INTO estados_cita (codigo, descripcion) VALUES (:c, :d) '
                     'ON CONFLICT (codigo) DO NOTHING'),
                {'c': cod, 'd': desc},
            )
    await engine.dispose()
    print('Semilla de estados de cita verificada.')

asyncio.run(main())
"
    ;;
  routes)
    "$PY" -c "
import sys; sys.path.insert(0, '$APP_DIR')
import core.base
from main import app
for p in sorted(app.openapi()['paths']):
    print(','.join(m.upper() for m in app.openapi()['paths'][p]), p)
"
    ;;
  *)
    echo "Uso: $0 {serve|test|pytest|migrate|seeds|routes}"
    exit 1
    ;;
esac
