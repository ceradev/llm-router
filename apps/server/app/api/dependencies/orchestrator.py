from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session

from app.catalog.registry import ModelRegistry
from packages.infrastructure.db.repositories.health_repository import HealthRepository
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository
from packages.infrastructure.db.session import engine, request_session_has_pending_writes
from packages.infrastructure.providers.registry import build_provider_clients
from packages.services.execution.fallback_executor import FallbackExecutor
from packages.services.model_selection.service import ModelSelector
from packages.services.orchestration.orchestrator import GatewayOrchestrator
from packages.services.prompt_evaluation import PromptEvaluator


from packages.infrastructure.config.settings import get_settings


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            if session.in_transaction():
                session.rollback()
            raise
        else:
            if request_session_has_pending_writes(session):
                session.commit()
            elif session.in_transaction():
                session.rollback()


def get_gateway_orchestrator(session: Session) -> GatewayOrchestrator:
    settings = get_settings()
    model_repository = ModelRepository(session)
    health_repository = HealthRepository(session)
    snapshot_repository = SnapshotRepository(session)
    selector = ModelSelector(
        model_repository=model_repository,
        snapshot_repository=snapshot_repository,
        health_repository=health_repository,
    )
    provider_clients = build_provider_clients(settings)
    fallback_registry = ModelRegistry()

    return GatewayOrchestrator(
        session=session,
        model_repository=model_repository,
        fallback_registry=fallback_registry,
        prompt_evaluator=PromptEvaluator(),
        selector=selector,
        executor=FallbackExecutor(
            provider_clients,
            health_repository=health_repository,
        ),
    )
