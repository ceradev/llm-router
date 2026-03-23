# LLM Gateway

Servidor FastAPI para un MVP de `Smart Router` entre múltiples modelos LLM.

## Objetivo

Este servicio recibe prompts y decide automáticamente:

- qué modelo usar
- con qué temperatura ejecutar
- qué fallback aplicar si falla el proveedor inicial

La implementación actual usa adapters `mock` para dejar la arquitectura montada sin depender todavía de APIs reales.

## Arquitectura

```text
Client
  -> FastAPI routes
    -> GatewayOrchestrator
      -> prompt classifier
      -> model selector
      -> model registry
      -> provider client
      -> fallback chain
```

Estructura principal:

```text
app/
  api/
    routes/
    schemas/
  gateway/
    orchestrator.py
    classify.py
    select.py
    fallback.py
    types.py
  catalog/
    registry.py
  providers/
    base.py
    openai/
    anthropic/
    groq/
    deepseek/
  main.py
main.py
```

## Flujo del request

1. Entra un prompt por `POST /v1/chat/completions`.
2. El servicio detecta intención: `general`, `analysis`, `code` o `creative`.
3. La policy combina intención + prioridad (`balanced`, `low_cost`, `high_quality`, `low_latency`).
4. Se elige una cadena de candidatos.
5. Si el primer modelo falla, se prueba el siguiente sin exponer el error al cliente.

## Ejecutar

```bash
cp .env.example .env
docker compose up -d postgres
uv run python main.py
```

La API queda disponible en `http://127.0.0.1:8000`.

## Base de datos PostgreSQL

La app usa `SQLModel` sobre PostgreSQL y crea las tablas automáticamente al arrancar.

Variables principales:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/llm_router
DATABASE_ECHO=false
```

Si quieres levantar sólo la base:

```bash
docker compose up -d postgres
```

## Endpoints

- `GET /`
- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

## Demo rápida

Prompt de código:

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Refactor this Python function and add tests",
    "priority": "balanced"
  }'
```

Fallback forzado:

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Design a rollout plan for a new AI feature",
    "priority": "high_quality",
    "simulate_failures": ["anthropic"]
  }'
```

## Siguiente paso recomendado

Sustituir los `client.py` actuales por integraciones reales y mantener intacto el pipeline de `app/gateway/`.
