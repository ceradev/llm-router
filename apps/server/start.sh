#!/bin/sh

echo "⏳ Waiting for database..."

# Esperar a la DB + migraciones
for i in $(seq 1 15); do
  alembic upgrade head && break
  echo "DB not ready yet..."
  sleep 2
done

echo "🚀 Starting API..."

uvicorn app.api.main:app --host 0.0.0.0 --port 8000