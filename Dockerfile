# ==========================================
# ETAPA 1: Builder (Compilación de ruedas/wheels)
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalar herramientas necesarias para compilar paquetes como asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .

# Compilar todas las librerías a formato wheel para no necesitar gcc en la imagen final
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# ==========================================
# ETAPA 2: Imagen Final (Ejecución Limpia)
# ==========================================
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar parches de seguridad del sistema y ÚNICAMENTE la librería en runtime para Postgres
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar las librerías precompiladas desde la etapa builder e instalarlas
COPY --from=builder /app/wheels /wheels
COPY backend/requirements.txt .
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copiar el código fuente
COPY backend/app ./app

# Crear usuario de sistema sin privilegios (Seguridad)
RUN addgroup --system appgroup && adduser --system --group appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]