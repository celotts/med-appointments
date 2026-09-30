#!/bin/bash
set -e

echo "=========================================="
echo "Medical Appointments - Container Startup"
echo "=========================================="

# Wait for database to be ready
echo "Waiting for database..."
until pg_isready -h ${POSTGRES_HOST:-postgres-vector} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-appointment}; do
  echo "Database not ready, waiting 2 seconds..."
  sleep 2
done
echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
cd /app
if [ -f alembic.ini ]; then
    alembic upgrade heads || echo "Migration failed (may already be applied), continuing..."
else
    echo "alembic.ini not found in /app, trying /app/app..."
    cd /app/app
    if [ -f ../alembic.ini ]; then
        alembic -c ../alembic.ini upgrade heads || echo "Migration failed (may already be applied), continuing..."
    else
        echo "WARNING: Could not find alembic.ini, skipping migrations"
    fi
fi

# Run seed script for large dataset
echo "Checking if large dataset seed is needed..."
python -c "
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import engine
from app.models.patient import Patient as PatientModel

async def check():
    async with AsyncSession(engine) as db:
        r = await db.execute(select(func.count()).select_from(PatientModel))
        count = r.scalar_one()
        print(f'Current patients: {count}')
        if count < 5000:
            print('SEED_NEEDED=true')
        else:
            print('SEED_NEEDED=false')

asyncio.run(check())
" > /tmp/seed_check.txt

SEED_NEEDED=$(grep "SEED_NEEDED=true" /tmp/seed_check.txt || echo "")

if [ -n "$SEED_NEEDED" ]; then
    echo "=========================================="
    echo "Seeding large dataset (this may take a minute)..."
    echo "=========================================="
    python /app/app/seed_large_dataset.py
    echo "=========================================="
    echo "Seed completed!"
    echo "=========================================="
else
    echo "Database already has sufficient data, skipping seed."
fi

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000