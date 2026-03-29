# LLM Router

LLM Router es una aplicacion full-stack para enrutar cada prompt al modelo de lenguaje mas adecuado segun la tarea, la prioridad y las capacidades disponibles del catalogo.

Su objetivo no es solo responder con un modelo, sino decidir mejor: analizar el prompt, rankear candidatos, ejecutar con fallback si hace falta y devolver una explicacion clara de por que ese modelo fue elegido.

## Que problema resuelve

Trabajar con multiples modelos LLM suele implicar estos problemas:

- elegir modelos a mano sin un criterio consistente
- repetir pruebas entre proveedores para comparar calidad, coste y velocidad
- no saber por que un modelo fue elegido
- no tener fallback si el proveedor o el modelo fallan
- perder trazabilidad de decisiones, intentos y resultados

LLM Router centraliza ese flujo en una sola capa de decision.

## Objetivos del proyecto

- seleccionar automaticamente el mejor modelo para cada request
- balancear calidad, coste y latencia segun la prioridad del usuario
- usar señales del prompt para inferir intencion y necesidades tecnicas
- exponer decisiones explicables, no solo un score final
- mantener historial y trazabilidad de requests, evaluaciones, intentos y feedback
- permitir sincronizar y mantener un catalogo real de modelos desde OpenRouter
- ofrecer una UI simple para experimentar con el router y entender el resultado

## Estado actual

Actualmente el proyecto ya incluye:

- frontend en Astro + React con flujo interactivo de recomendacion
- backend en FastAPI con pipeline de routing y fallback
- persistencia en PostgreSQL via SQLModel
- migraciones con Alembic
- sincronizacion de modelos desde OpenRouter
- historial de requests por sesion
- feedback por request
- mock offline en frontend si la API no responde
- tests backend y build del frontend

## Features principales

### Routing inteligente

- clasificacion del prompt por intencion: `general`, `analysis`, `code`, `creative`
- evaluacion heuristica del prompt: complejidad, necesidad de JSON, tools, reasoning y code
- ranking de candidatos por calidad, latencia, coste y pesos de prioridad
- soporte para `balanced`, `high_quality`, `low_cost` y `low_latency`
- ajustes por `use_cases`, `preferred_providers` y `response_depth`

### Ejecucion robusta

- seleccion del mejor candidato disponible
- fallback automatico si falla el modelo inicial
- registro de intentos con estado y latencia
- exposicion del modelo recomendado y del modelo finalmente ejecutado

### Explicabilidad

- respuesta del gateway con resumen de ranking
- explicacion textual del por que del mejor modelo
- ranking completo con scores y explicacion por candidato
- capacidades del modelo: JSON, tools, tier, free y capacidades del catalogo

### Persistencia y trazabilidad

- requests almacenados con sesion, prioridad e intencion
- analisis del request persistido
- evaluaciones por modelo persistidas por request
- ejecuciones e intentos persistidos
- feedback del usuario asociado a cada request

### Catalogo de modelos

- seed inicial opcional de modelos curados
- auto-sync desde OpenRouter si el catalogo esta vacio
- sync manual via endpoint
- sync al arrancar y sync periodico configurables

### Frontend

- landing interactiva con analisis y resultados
- vista de resultados con mejor modelo, alternativas y comparativas
- i18n en ingles y espanol
- historial por sesion
- modo offline con payload mock cuando falla la API

## Como funciona

Flujo simplificado de una request:

1. El usuario envia un prompt desde la UI o la API.
2. El backend evalua el prompt y deduce intencion y señales tecnicas.
3. Se cargan candidatos elegibles del catalogo.
4. El motor de scoring calcula el ranking segun prioridad y contexto.
5. Se guarda el analisis y las evaluaciones en base de datos.
6. Se intenta ejecutar el mejor modelo.
7. Si falla, entra la cadena de fallback.
8. Se guarda la ejecucion final y los intentos.
9. La API devuelve contenido, ranking, explicacion y metadatos de routing.
10. El frontend transforma esa respuesta en una vista entendible para el usuario.

## Arquitectura

```text
apps/web
  -> UI Astro + React
  -> shared/api/*
  -> FastAPI backend

apps/server/app/api
  -> routes
  -> dependencies

packages/services
  -> prompt_evaluation
  -> model_selection
  -> execution
  -> orchestration
  -> sync

packages/domain
  -> tipos de dominio del gateway y modelos

packages/infrastructure
  -> config
  -> db
  -> providers

PostgreSQL
  -> requests, analysis, evaluations, attempts, executions, feedback, models, providers
```

## Stack tecnico

### Frontend

- Astro 6
- React 19
- TypeScript
- Tailwind CSS 4
- Framer Motion

### Backend

- Python 3.11+
- FastAPI
- SQLModel
- Pydantic Settings
- Alembic
- HTTPX
- Uvicorn

### Infra y datos

- PostgreSQL 16
- Docker
- Docker Compose
- Adminer para inspeccion local de base de datos

### Tooling actual

- `bun` para la app web
- `uv` para el backend Python
- `pytest` para tests backend

## Estructura del repositorio

```text
.
├─ apps/
│  ├─ server/
│  │  ├─ app/
│  │  │  ├─ api/
│  │  │  │  ├─ dependencies/
│  │  │  │  └─ routes/
│  │  │  └─ catalog/
│  │  ├─ tests/
│  │  └─ pyproject.toml
│  └─ web/
│     ├─ src/
│     │  ├─ app/
│     │  ├─ contexts/
│     │  ├─ features/
│     │  ├─ i18n/
│     │  ├─ pages/
│     │  └─ shared/
│     └─ package.json
├─ migrations/
├─ packages/
│  ├─ core/
│  ├─ domain/
│  ├─ infrastructure/
│  ├─ schemas/
│  └─ services/
├─ Dockerfile
├─ docker-compose.yml
└─ README.md
```

## Modulos importantes

### Backend

- `apps/server/app/api/routes/gateway.py`
  Endpoints principales del router.

- `packages/services/orchestration/orchestrator.py`
  Orquesta el flujo completo: evaluacion, seleccion, persistencia, ejecucion y respuesta.

- `packages/services/prompt_evaluation/`
  Analiza el prompt y genera señales para routing.

- `packages/services/model_selection/`
  Construye el ranking de modelos candidatos.

- `packages/services/execution/`
  Ejecuta el modelo y gestiona fallback.

- `packages/services/sync/`
  Sincroniza el catalogo desde OpenRouter.

- `packages/infrastructure/db/`
  Modelos, repositorios, sesion, seeds y utilidades de migracion.

### Frontend

- `apps/web/src/app/LLMRouterApp.tsx`
  Contenedor principal de la experiencia interactiva.

- `apps/web/src/shared/api/gateway.ts`
  Cliente del endpoint avanzado del gateway.

- `apps/web/src/shared/api/converters.ts`
  Convierte la respuesta backend al payload que consume la UI.

- `apps/web/src/shared/api/recommend.ts`
  Orquesta llamada real a API y fallback mock offline.

- `apps/web/src/features/results/`
  Renderiza la vista de resultados y comparacion de modelos.

## Endpoints actuales

### Salud

- `GET /health`

### Gateway

- `GET /v1/models`
- `POST /v1/chat/completions/simple`
- `POST /v1/chat/completions/advanced`

### Providers

- `GET /v1/providers`

### Historial y feedback

- `GET /v1/requests`
- `GET /v1/requests/{request_id}`
- `POST /v1/requests/{request_id}/feedback`

### Sync

- `POST /v1/sync/models`

## Ejemplo de request avanzada

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions/advanced \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: demo-session" \
  -d '{
    "prompt": "Design a rollout plan for a new AI feature",
    "priority": "high_quality",
    "use_cases": ["api"],
    "preferred_providers": ["openai", "anthropic"],
    "response_depth": "detailed",
    "require_json": false
  }'
```

## Respuesta del gateway

La respuesta avanzada devuelve, entre otros, estos campos:

- `content`: respuesta generada
- `provider`: proveedor final usado
- `model_id`: modelo que realmente respondio
- `recommended_model_id`: mejor candidato antes de fallback
- `response_latency_ms`: latencia real observada en la ejecucion exitosa
- `intent`: intencion detectada
- `priority`: prioridad aplicada
- `routing_reason`: razon breve del routing
- `explanation`: explicacion legible para UI
- `ranking_summary`: resumen de mejores picks
- `ranking`: ranking completo con scores y detalle
- `fallback_used`: si hubo fallback
- `candidate_models`: ids considerados
- `attempts`: intentos ejecutados

## Base de datos

El sistema persiste informacion operativa y analitica.

Entidades principales:

- `llm_models`
- `providers`
- `llm_requests`
- `request_analysis`
- `model_evaluation`
- `llm_attempt`
- `llm_execution`
- `llm_feedback`

Las migraciones viven en `migrations/` y el proyecto ya incluye schema inicial y migraciones posteriores.

## Configuracion

Variables importantes en `.env`:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/llm_router
OPENROUTER_API_KEY=
SEED_MODELS_ON_STARTUP=false
OPENROUTER_AUTO_SYNC_ON_EMPTY_CATALOG=true
OPENROUTER_SYNC_ON_STARTUP=true
OPENROUTER_ENABLE_PERIODIC_SYNC=true
OPENROUTER_SYNC_INTERVAL_HOURS=6
```

Notas:

- no commits claves reales en `.env`
- usa `.env.example` como plantilla
- si `OPENROUTER_AUTO_SYNC_ON_EMPTY_CATALOG=true`, el backend intentara poblar el catalogo cuando no encuentre modelos usables

## Como levantar el proyecto

### Opcion 1: Docker Compose

Levanta PostgreSQL, backend y Adminer.

```bash
cp .env.example .env
docker compose up --build
```

Servicios:

- backend: `http://127.0.0.1:8000`
- postgres: `localhost:5432`
- adminer: `http://127.0.0.1:8080`

### Opcion 2: Desarrollo local por separado

#### Backend

Desde la raiz, con PostgreSQL corriendo:

```bash
docker compose up -d postgres
uv run --project apps/server uvicorn app.api.main:app --app-dir apps/server --reload
```

Si necesitas que Python resuelva bien el monorepo en local, normalmente se usa:

```bash
PYTHONPATH=.:apps/server
```

En Windows PowerShell:

```powershell
$env:PYTHONPATH='.;apps/server'
uv run --project apps/server uvicorn app.api.main:app --app-dir apps/server --reload
```

#### Frontend

```bash
cd apps/web
bun install
bun run dev
```

La app web queda disponible normalmente en `http://127.0.0.1:4321`.

## Comandos utiles

### Frontend

```bash
cd apps/web
bun install
bun run dev
bun run build
```

### Backend

```bash
uv run --project apps/server pytest apps/server/tests
uv run --project apps/server uvicorn app.api.main:app --app-dir apps/server --reload
```

### Base de datos

```bash
docker compose up -d postgres
```

### Sync de modelos

```bash
curl -X POST http://127.0.0.1:8000/v1/sync/models
```

## Comportamiento offline del frontend

El frontend no se rompe si la API falla.

`apps/web/src/shared/api/recommend.ts` hace esto:

- intenta llamar al gateway real
- si falla la request y no fue por abort, genera un payload mock local
- renderiza una experiencia de demo sin datos live de routing

Esto permite seguir iterando la UI aunque el backend no este disponible.

## Testing y validacion

Estado validado hasta ahora:

- tests backend pasando
- build de `apps/web` pasando

Comandos habituales:

```bash
uv run --project apps/server pytest apps/server/tests
cd apps/web && bun run build
```

## Limitaciones actuales

- la calidad del routing depende del catalogo y sus scores disponibles
- la evaluacion del prompt es heuristica, no un clasificador entrenado aparte
- la UI hoy esta centrada en recomendacion y exploracion, no en un panel operativo completo
- no hay autenticacion de usuarios; el historial se segmenta por `X-Session-Id`

## Roadmap natural

- mejorar observabilidad y metricas del router
- añadir auth y sesiones persistentes de usuario
- ampliar feedback loop para recalibrar scoring
- exponer panel administrativo para providers, sync y catalogo
- añadir mas fuentes de catalogo ademas de OpenRouter
- endurecer tests end-to-end entre frontend y backend

## Resumen

LLM Router ya es mas que un demo visual: tiene backend con scoring, fallback, persistencia, sync de catalogo, historial y una UI capaz de explicar la recomendacion principal de forma clara.

La idea central del proyecto es simple: dejar de elegir modelos por intuicion y empezar a enrutar prompts con criterio, contexto y trazabilidad.
