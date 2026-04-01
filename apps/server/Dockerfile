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
COPY . .

# dump
COPY production_dump.sql ./production_dump.sql

ENV PYTHONPATH=/app

EXPOSE 8000

CMD sh -c "\
echo '⏳ Waiting for database...' && \
for i in $(seq 1 20); do \
  python -c \"import psycopg, os; psycopg.connect(os.environ['DATABASE_URL'])\" \
  && break || sleep 2; \
done && \
echo '📦 Running migrations...' && \
alembic upgrade head && \
echo '🗄️ Running seed once...' && \
python -c \"\
import psycopg, os; \
conn=psycopg.connect(os.environ['DATABASE_URL']); \
cur=conn.cursor(); \
cur.execute('CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT)'); \
cur.execute(\\\"SELECT value FROM app_metadata WHERE key='seed_done'\\\"); \
res=cur.fetchone(); \
\
if not res: \
    f=open('production_dump.sql'); \
    cur.execute(f.read()); \
    cur.execute(\\\"INSERT INTO app_metadata (key,value) VALUES ('seed_done','true')\\\"); \
    conn.commit(); \
\
conn.close(); \
\" && \
echo '🚀 Starting API...' && \
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 \
"