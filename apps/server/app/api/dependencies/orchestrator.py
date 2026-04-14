from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session

from app.catalog.registry import ModelRegistry
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.session import engine
from packages.infrastructure.providers.registry import build_provider_clients
from packages.services.execution.fallback_executor import FallbackExecutor
from packages.services.model_selection.service import ModelSelector
from packages.services.orchestration.orchestrator import GatewayOrchestrator
from packages.services.prompt_evaluation import PromptEvaluator


from packages.infrastructure.config.settings import get_settings


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.commit()


def get_gateway_orchestrator(session: Session) -> GatewayOrchestrator:
    settings = get_settings()
    model_repository = ModelRepository(session)
    selector = ModelSelector(model_repository=model_repository)
    provider_clients = build_provider_clients(settings)

    return GatewayOrchestrator(
        session=session,
        model_repository=model_repository,
        fallback_registry=provider_clients,
        prompt_evaluator=PromptEvaluator(),
        selector=selector,
        executor=FallbackExecutor(provider_clients),
    )
