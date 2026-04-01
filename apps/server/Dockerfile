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
COPY apps/server/dump.sql ./dump.sql

ENV PYTHONPATH=/app:/app/apps/server

EXPOSE 8000

# ---- CMD (wait + migrate + seed once + run) ----
CMD sh -c "\
echo '⏳ Waiting for database...' && \
for i in $(seq 1 20); do \
  python -c \"import psycopg, os; psycopg.connect(os.environ['DATABASE_URL'])\" \
  && break || echo 'DB not ready...' && sleep 2; \
done && \
echo '📦 Running migrations...' && \
alembic upgrade head && \
echo '🗄️ Checking seed status...' && \
python - <<EOF
import psycopg, os

conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# crear tabla de control
cur.execute('''
CREATE TABLE IF NOT EXISTS app_metadata (
  key TEXT PRIMARY KEY,
  value TEXT
)
''')

# comprobar si ya se ejecutó el dump
cur.execute(\"SELECT value FROM app_metadata WHERE key='seed_done'\")
result = cur.fetchone()

if not result:
    print('🚀 Running initial dump...')
    with open('dump.sql') as f:
        cur.execute(f.read())
    cur.execute(\"INSERT INTO app_metadata (key, value) VALUES ('seed_done','true')\")
    conn.commit()
else:
    print('✅ Seed already executed, skipping...')

conn.close()
EOF
&& \
echo '🚀 Starting API...' && \
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 \
"