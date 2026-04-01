FROM python:3.11-slim

WORKDIR /app

# ---- system deps ----
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc curl \
    && rm -rf /var/lib/apt/lists/*

# ---- python deps ----
RUN pip install --no-cache-dir --upgrade pip

COPY apps/server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---- copiar código ----
COPY apps/server ./apps/server
COPY packages ./packages

# (opcional)
COPY apps/server/production_dump.sql ./production_dump.sql

WORKDIR /app/apps/server

ENV PYTHONPATH=/app/apps/server

EXPOSE 8000

CMD ["sh", "-c", "\
echo '⏳ Waiting for database...' && \
until python -c \"import psycopg, os; psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://'))\"; do \
  echo 'DB not ready...'; \
  sleep 2; \
done && \
echo '📦 Running migrations...' && \
alembic -c alembic.ini upgrade head upgrade head && \
echo '🚀 Starting API...' && \
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 \
"]