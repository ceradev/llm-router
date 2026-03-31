# Changelog

All notable changes to this project are documented in this file.

## v1.0.0-rc.1 - 2026-03-31

### Added

- Intelligent LLM routing with prompt analysis and priority-aware ranking.
- Fallback chain support to improve execution reliability when a model call fails.
- PostgreSQL persistence for requests, routing analysis, evaluations, attempts, and feedback.
- OpenRouter model synchronization flow for catalog refresh and operational maintenance.
- Frontend experience with bilingual i18n support (English and Spanish).
- FAQ modal and UX improvements for discovery and onboarding.
- Production-ready Docker deployment path under `infra/docker/llm-router/`.

### Notes

- This release candidate is intended for production validation before final `v1.0.0`.
