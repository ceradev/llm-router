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

COPY . /app

ENV PYTHONPATH=/app:/app/apps/server

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
