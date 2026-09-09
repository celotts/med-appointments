# ==========================================
# ETAPA 1: Builder (Compilación de ruedas/wheels)
# ==========================================
FROM python:3.11-alpine3.22 AS builder

WORKDIR /app

# Instalar herramientas necesarias para compilar paquetes como asyncpg
RUN apk update && apk upgrade --no-cache && apk add --no-cache \
    build-base \
    postgresql-dev

COPY backend/requirements.txt .

# Compilar todas las librerías a formato wheel para no necesitar gcc en la imagen final
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# ==========================================
# ETAPA 2: Imagen Final (Ejecución Limpia)
# ==========================================
FROM python:3.11-alpine3.22 AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Instalar parches de seguridad y ÚNICAMENTE la librería en runtime para Postgres
RUN apk update && apk upgrade --no-cache && apk add --no-cache libpq

# Copiar las librerías precompiladas desde la etapa builder e instalarlas
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

# Copiar el código fuente asegurando que quede dentro de la carpeta app
COPY backend/app /app/app

# Crear usuario de sistema sin privilegios (Seguridad)
RUN addgroup -S appgroup && adduser -S -G appgroup appuser
USER appuser

EXPOSE 8000

# Apuntar correctamente al módulo dentro del paquete app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]