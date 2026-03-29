# Changelog

## Added

- Backend modular architecture under `packages/` for domain, core, infrastructure, schemas, and services.
- FastAPI app structure in `apps/server/app/api` with routes for health, gateway, providers, requests, and sync.
- LLM orchestration pipeline with prompt evaluation, model selection, fallback execution, and request analysis.
- Database layer with SQLModel entities, repositories, Alembic config, and initial migrations.
- Provider sync flow and OpenRouter integration utilities.
- Request/session history support and response mappers.
- Frontend feature-based app structure for landing, analyzing, history, and results flows.
- New shared UI components, backgrounds, navbar/footer, icons, and API client helpers.
- Contexts for theme, i18n, and background motion.
- Automated tests for advanced options, prompt evaluation, providers route, requests route, scoring engine, and fallback selection.
- Docker and local environment setup files plus expanded backend/frontend docs.

## Changed

- Reworked the web app UX around a full LLM router journey: prompt entry, analysis state, and results visualization.
- Refactored frontend into modular features and shared primitives.
- Expanded README and project documentation to cover setup and architecture.
- Updated project structure to separate `apps/server`, `apps/web`, `packages`, and `migrations`.
- Improved routing, scoring logic, and model recommendation behavior.

## Technical Highlights

- New migrations:
  - `d954d9a49510_initial_schema.py`
  - `b2c3d4e5f6g7_reassign_models_to_upstream_providers.py`
  - `f1a2b3c4d5e6_add_llm_requests_session_id.py`
- Large frontend additions:
  - `apps/web/src/features/landing/*`
  - `apps/web/src/features/analyzing/*`
  - `apps/web/src/features/results/*`
  - `apps/web/src/shared/api/*`
- Large backend additions:
  - `packages/services/orchestration/orchestrator.py`
  - `packages/services/sync/openrouter_sync_service.py`
  - `packages/infrastructure/db/repositories/*`
  - `apps/server/app/api/routes/requests.py`

## Notes

- This changelog summarizes changes already present on `development` compared with `main`.
- Local uncommitted `.env` and `__pycache__` changes are intentionally excluded from these notes.
