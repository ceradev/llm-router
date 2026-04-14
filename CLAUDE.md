# LLM Router — Project Map

## Estructura de paquetes
```
packages/
  core/scoring/engine.py                          → ScoringEngine, compute_model_score
  services/orchestration/orchestrator.py          → GatewayOrchestrator (entrada principal)
  services/model_selection/service.py             → ModelSelector.build_decision
  services/execution/fallback_executor.py         → FallbackExecutor.run
  services/prompt_evaluation/                     → PromptEvaluator
  services/sync/openrouter_sync_service.py        → OpenRouterSyncService
  infrastructure/db/repositories/                → repos: request, analysis, eval, execution, attempt, metrics
  infrastructure/db/models/                      → SQLModel ORM models
  infrastructure/providers/registry.py           → build_provider_clients (OpenAI, Anthropic, Groq, DeepSeek, OpenRouter)
  infrastructure/config/settings.py              → get_settings()
  domain/gateway.py                              → tipos: GatewayTask, RoutingDecision, ScoredCandidate, GatewayExecutionResult
  domain/models.py                              → ModelProfile

apps/
  server/app/api/routes/                        → FastAPI routes: gateway, requests, providers, admin, metrics, sync, health
  server/app/api/dependencies/orchestrator.py  → DI wiring del GatewayOrchestrator
  server/tests/                                → pytest tests
  web/src/                                     → Astro + React frontend
```

## Flujo principal
1. Request → `gateway.py` / `requests.py`
2. `GatewayOrchestrator.execute(task)`
3. `PromptEvaluator.evaluate(prompt)` → intent, complexity, skills requeridos
4. `ModelSelector.build_decision()` → carga modelos DB, aplica scoring
5. `ScoringEngine.compute_model_score()` → quality + latency + cost + bonos contextuales
6. `FallbackExecutor.run()` → llama proveedor, fallback si falla
7. Persiste: request → analysis → evaluations → attempts → execution → metrics

## Stack
- Backend: Python 3.11+, FastAPI, SQLModel, Alembic, HTTPX
- Frontend: Astro 6, React 19, TypeScript, Tailwind, Framer Motion
- DB: PostgreSQL 16
- Infra: Docker Compose, VPS CubePath (`vps22425.cubepath.net`)
- Tooling: `uv` + `pytest` (backend), `bun` (frontend)
