FROM python:3.11-slim

WORKDIR /app

# ---- system deps ----
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc curl \
    && rm -rf /var/lib/apt/lists/*

# ---- python deps ----
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---- copiar código ----
  COPY apps/server ./apps/server
  COPY packages ./packages
  COPY migrations ./migrations

# dump
COPY apps/server/production_dump.sql ./production_dump.sql

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "\
echo '⏳ Waiting for database...' && \
until python -c \"import psycopg, os; psycopg.connect(os.environ['DATABASE_URL'])\"; do \
  echo 'DB not ready...'; \
  sleep 2; \
done && \
echo '📦 Running migrations...' && \
alembic upgrade head && \
echo '🚀 Starting API...' && \
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 \
"]