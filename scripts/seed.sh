#!/bin/bash
# Carga los datos de prueba (catálogos + datos de ejemplo) en la BD.
# Uso:  ./scripts/seed.sh [docker|podman]   (por defecto: docker)
# Equivale a:  make seed            (Docker)
#              make seed-podman     (Podman)

set -e

ENGINE="${1:-docker}"
PG_CONTAINER="${PG_CONTAINER:-medical_pgvector}"
PG_USER="${PG_USER:-postgres}"
PG_DB="${PG_DB:-appointment}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Motor: $ENGINE. Esperando a que PostgreSQL esté listo..."
until "$ENGINE" exec "$PG_CONTAINER" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; do
  sleep 1
done

echo "Esperando al superusuario admin@medapp.com..."
for _ in $(seq 1 60); do
  if [ "$("$ENGINE" exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT 1 FROM users WHERE email='admin@medapp.com'" 2>/dev/null | tr -d '[:space:]')" = "1" ]; then
    break
  fi
  sleep 1
done

echo "Cargando catálogos..."
"$ENGINE" exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 \
  < "$DIR/script_BD/seeds/seed_catalogs.sql"

echo "Cargando datos de ejemplo..."
"$ENGINE" exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 \
  < "$DIR/script_BD/seeds/seed_sample.sql"

echo "Datos de prueba cargados."
