# ==========================================
# ETAPA 1: Builder (Compilación de ruedas/wheels)
# ==========================================
FROM python:3.12-slim-trixie AS builder

WORKDIR /app

# Instalar herramientas necesarias para compilar paquetes como asyncpg
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
COPY backend/requirements-dev.txt .

# Compilar todas las librerías a formato wheel para no necesitar gcc en la imagen final
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Dependencias de pruebas (pytest) para certificar el desarrollo con `make test`
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements-dev.txt

# ==========================================
# ETAPA 2: Imagen Final (Ejecución Limpia)
# ==========================================
FROM python:3.12-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Instalar parches de seguridad y ÚNICAMENTE la librería en runtime para Postgres
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copiar las librerías precompiladas desde la etapa builder e instalarlas
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

# Copiar el código fuente asegurando que quede dentro de la carpeta app
COPY backend/app /app/app

# Copiar script de semilla y entrypoint
COPY backend/app/seed_large_dataset.py /app/app/seed_large_dataset.py
COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh
COPY backend/alembic.ini /app/alembic.ini
COPY backend/alembic /app/alembic
RUN chmod +x /app/docker-entrypoint.sh

# Configuración de pytest y suite de pruebas para `make test`
COPY backend/pytest.ini /app/pytest.ini
COPY backend/tests /app/tests

# Instalar cliente postgres para pg_isready
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

# Usar entrypoint que espera DB, migra y semilla
ENTRYPOINT ["/app/docker-entrypoint.sh"]