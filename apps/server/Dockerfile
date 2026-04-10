FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
    "alembic>=1.14.0" \
    "fastapi>=0.135.2" \
    "uvicorn[standard]>=0.42.0" \
    "sqlmodel>=0.0.24" \
    "psycopg[binary]>=3.2.10" \
    "httpx>=0.27.0" \
    "pydantic-settings>=2.11.0"

# ---- copiar código ----
COPY apps/server ./apps/server
COPY apps/server/alembic.ini ./alembic.ini
COPY packages ./packages
COPY migrations ./migrations

WORKDIR /app/apps/server

ENV PYTHONPATH=/app:/app/apps/server

EXPOSE 8000

CMD ["sh", "-c", "\
echo '⏳ Waiting for database...' && \
until python3 -c 'import psycopg, os; psycopg.connect(os.environ[\"DATABASE_URL\"].replace(\"postgresql+psycopg://\", \"postgresql://\"))'; do \
  echo 'DB not ready...'; \
  sleep 2; \
done && \
echo '📦 Running migrations...' && \
alembic -c alembic.ini upgrade head && \
echo '🚀 Starting API...' && \
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 \
"]