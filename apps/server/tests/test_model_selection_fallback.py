from __future__ import annotations

import pytest

from packages.domain.gateway import GatewayTask, Intent, NoModelsAvailableError, Priority
from packages.domain.models import Capability, ModelProfile
from packages.infrastructure.db.repositories.model_repository import ModelRepository, ModelRoutingRow
from packages.services.model_selection.service import ModelSelector
from packages.services.prompt_evaluation import PromptEvaluator


class EmptyModelRepository(ModelRepository):
    def __init__(self) -> None:  # type: ignore[override]
        self.session = None  # type: ignore[assignment]

    def list_routing_candidates(self, *, priority: Priority, require_json: bool):  # type: ignore[override]
        return []


def test_model_selector_raises_when_db_has_no_candidates() -> None:
    selector = ModelSelector(model_repository=EmptyModelRepository())

    task = GatewayTask(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=128,
        require_json=False,
        simulate_failures=[],
    )

    evaluation = PromptEvaluator().evaluate("hello")

    with pytest.raises(NoModelsAvailableError):
        selector.build_decision(task=task, intent=Intent.GENERAL, evaluation=evaluation)


def _identical_tie_profile(*, model_id: str) -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider="p",
        quality_score=3,
        latency_score=3,
        cost_score=3,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
        supports_tools=False,
    )


class TieModelRepository(ModelRepository):
    """Two candidates with identical scores; repository order is z then a."""

    def __init__(self) -> None:  # type: ignore[override]
        self.session = None  # type: ignore[assignment]

    def list_routing_candidates(self, *, priority: Priority, require_json: bool):  # type: ignore[override]
        return [
            ModelRoutingRow(
                model=_identical_tie_profile(model_id="z/tie"),
                priority_weight=100,
                db_model_id=2,
            ),
            ModelRoutingRow(
                model=_identical_tie_profile(model_id="a/tie"),
                priority_weight=100,
                db_model_id=1,
            ),
        ]


def test_model_selector_tiebreaks_by_model_id_alphabetically() -> None:
    selector = ModelSelector(model_repository=TieModelRepository())
    task = GatewayTask(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=128,
        require_json=False,
        simulate_failures=[],
    )
    evaluation = PromptEvaluator().evaluate("hello")
    decision = selector.build_decision(task=task, intent=Intent.GENERAL, evaluation=evaluation)

    assert decision.candidates[0].model_id == "a/tie"
    assert decision.candidates[1].model_id == "z/tie"
    assert decision.scored_candidates[0].final_score == decision.scored_candidates[1].final_score
