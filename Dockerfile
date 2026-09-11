# ==========================================
# ETAPA 1: Builder (Compilación de ruedas/wheels)
# ==========================================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Instalar herramientas necesarias para compilar paquetes como asyncpg
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .

# Compilar todas las librerías a formato wheel para no necesitar gcc en la imagen final
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# ==========================================
# ETAPA 2: Imagen Final (Ejecución Limpia)
# ==========================================
FROM python:3.12-slim-bookworm AS runtime

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

# Usuario de sistema (comentado por problemas de construcción en algunos entornos)
# RUN addgroup -S appgroup && adduser -S -G appgroup appuser
# USER appuser

EXPOSE 8000

# Apuntar correctamente al módulo dentro del paquete app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]