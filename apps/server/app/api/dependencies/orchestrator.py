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


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.commit()


def get_gateway_orchestrator(session: Session) -> GatewayOrchestrator:
    fallback_registry = ModelRegistry()
    model_repository = ModelRepository(session)
    selector = ModelSelector(model_repository=model_repository)

    return GatewayOrchestrator(
        session=session,
        model_repository=model_repository,
        fallback_registry=fallback_registry,
        prompt_evaluator=PromptEvaluator(),
        selector=selector,
        executor=FallbackExecutor(build_provider_clients()),
    )
