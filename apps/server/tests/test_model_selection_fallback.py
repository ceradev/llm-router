from __future__ import annotations

from sqlmodel import Session

from app.catalog.registry import ModelRegistry
from packages.domain.gateway import GatewayTask, Intent, Priority
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.services.model_selection.service import ModelSelector


class EmptyModelRepository(ModelRepository):
    def __init__(self) -> None:  # type: ignore[override]
        self.session = None  # type: ignore[assignment]

    def list_routing_candidates(self, *, intent: Intent, priority: Priority, require_json: bool):  # type: ignore[override]
        return []


def test_model_selector_falls_back_to_catalog_when_db_empty() -> None:
    selector = ModelSelector(
        model_repository=EmptyModelRepository(),
        fallback_registry=ModelRegistry(),
    )

    task = GatewayTask(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=128,
        require_json=False,
        simulate_failures=[],
    )

    decision = selector.build_decision(task=task, intent=Intent.GENERAL)
    assert decision.candidates, "expected non-empty candidates from catalog fallback"

