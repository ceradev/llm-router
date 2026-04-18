from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlmodel import Session

from app.catalog.registry import ModelRegistry
from app.api.dependencies.orchestrator import get_gateway_orchestrator
from packages.infrastructure.db.repositories.health_repository import HealthRepository
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository
from packages.services.execution.fallback_executor import FallbackExecutor
from packages.services.model_selection.service import ModelSelector
from packages.services.orchestration.orchestrator import GatewayOrchestrator


def test_get_gateway_orchestrator_builds_health_and_snapshot_aware_runtime_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock(spec=Session)
    provider_clients = {"openrouter": object(), "openai": object()}

    monkeypatch.setattr(
        "app.api.dependencies.orchestrator.get_settings",
        lambda: object(),
    )
    monkeypatch.setattr(
        "app.api.dependencies.orchestrator.build_provider_clients",
        lambda _settings: provider_clients,
    )

    orchestrator = get_gateway_orchestrator(session)

    assert isinstance(orchestrator, GatewayOrchestrator)
    assert orchestrator.session is session
    assert isinstance(orchestrator.model_repository, ModelRepository)
    assert orchestrator.model_repository.session is session

    assert isinstance(orchestrator.fallback_registry, ModelRegistry)

    assert isinstance(orchestrator.selector, ModelSelector)
    assert orchestrator.selector.model_repository is orchestrator.model_repository
    assert isinstance(orchestrator.selector.health_repository, HealthRepository)
    assert orchestrator.selector.health_repository.session is session
    assert isinstance(orchestrator.selector.snapshot_repository, SnapshotRepository)
    assert orchestrator.selector.snapshot_repository.session is session

    assert isinstance(orchestrator.executor, FallbackExecutor)
    assert orchestrator.executor.providers is provider_clients
    assert isinstance(orchestrator.executor.health_repository, HealthRepository)
    assert orchestrator.executor.health_repository.session is session

    assert orchestrator.executor.health_repository is orchestrator.selector.health_repository
