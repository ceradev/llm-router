from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session

from app.catalog.registry import ModelRegistry
from packages.core.classification.prompt_classifier import PromptClassifier
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.session import get_session
from packages.infrastructure.providers.registry import build_provider_clients
from packages.services.execution.fallback_executor import FallbackExecutor
from packages.services.model_selection.service import ModelSelector
from packages.services.orchestration.orchestrator import GatewayOrchestrator


def get_db_session() -> Generator[Session, None, None]:
    # Delegate lifecycle handling to the infrastructure layer.
    yield from get_session()


def get_gateway_orchestrator(session: Session) -> GatewayOrchestrator:
    fallback_registry = ModelRegistry()
    model_repository = ModelRepository(session)
    selector = ModelSelector(model_repository=model_repository, fallback_registry=fallback_registry)

    return GatewayOrchestrator(
        model_repository=model_repository,
        fallback_registry=fallback_registry,
        classifier=PromptClassifier(),
        selector=selector,
        executor=FallbackExecutor(build_provider_clients()),
    )

