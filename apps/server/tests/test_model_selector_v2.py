from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from packages.core.scoring.engine import ScoreBreakdown
from packages.domain.gateway import GatewayTask, Intent, ModelTier, Priority
from packages.domain.models import Capability, ModelProfile
from packages.infrastructure.db.repositories.model_repository import ModelRepository, ModelRoutingRow
from packages.infrastructure.db.repositories.health_repository import HealthRepository
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository
from packages.services.model_selection.service import ModelSelector
from packages.services.prompt_evaluation.types import PromptEvaluationResult

@pytest.fixture
def mock_model_repo():
    repo = MagicMock(spec=ModelRepository)
    repo.session = None
    # Model 1: Verified (Tier 1)
    m1 = ModelProfile(
        model_id="gpt-4", provider="openai", 
        quality_score=5, latency_score=3, cost_score=2, 
        default_temperature=0.7, evaluation_status="verified", context_window=8192
    )
    # Model 2: Cataloged (Tier 2)
    m2 = ModelProfile(
        model_id="llama-3", provider="meta", 
        quality_score=4, latency_score=4, cost_score=4, 
        default_temperature=0.7, evaluation_status="cataloged", context_window=8192
    )
    
    repo.list_routing_candidates.return_value = [
        ModelRoutingRow(db_model_id=1, model=m1, priority_weight=100),
        ModelRoutingRow(db_model_id=2, model=m2, priority_weight=100),
    ]
    return repo

@pytest.fixture
def mock_health_repo():
    repo = MagicMock(spec=HealthRepository)
    repo.get_broken_model_ids.return_value = set()
    repo.get_status.return_value = "healthy"
    return repo

@pytest.fixture
def mock_snapshot_repo():
    repo = MagicMock(spec=SnapshotRepository)
    repo.get_latest_snapshot.return_value = None
    return repo

def test_model_selector_tiers_filtering(mock_model_repo, mock_health_repo, mock_snapshot_repo):
    selector = ModelSelector(
        model_repository=mock_model_repo,
        health_repository=mock_health_repo,
        snapshot_repository=mock_snapshot_repo
    )
    
    evaluation = PromptEvaluationResult(
        intent="general", complexity_score=0.5, 
        requires_code=False, requires_reasoning=False, requires_tools=False,
        requires_json=False, estimated_tokens=100, keywords=[]
    )
    
    # Task NOT in discovery mode -> should only return Tier 1 (verified)
    task_normal = GatewayTask(
        prompt="hello", priority=Priority.BALANCED, 
        temperature=None, max_tokens=None, require_json=False,
        discovery_mode=False
    )
    
    decision_normal = selector.build_decision(
        task=task_normal, intent=Intent.GENERAL, evaluation=evaluation
    )
    
    assert len(decision_normal.candidates) == 1
    assert decision_normal.candidates[0].model_id == "gpt-4"
    assert decision_normal.scored_candidates[0].tier == ModelTier.TIER1_VERIFIED

    # Task IN discovery mode -> should return both Tier 1 and Tier 2
    task_discovery = GatewayTask(
        prompt="hello", priority=Priority.BALANCED, 
        temperature=None, max_tokens=None, require_json=False,
        discovery_mode=True
    )
    
    decision_discovery = selector.build_decision(
        task=task_discovery, intent=Intent.GENERAL, evaluation=evaluation
    )
    
    assert len(decision_discovery.candidates) == 2
    ids = [c.model_id for c in decision_discovery.candidates]
    assert "gpt-4" in ids
    assert "llama-3" in ids

def test_selector_deduplicates_same_model_id(mock_model_repo, mock_health_repo, mock_snapshot_repo):
    duplicate = ModelProfile(
        model_id="gpt-4",
        provider="openai",
        quality_score=5,
        latency_score=3,
        cost_score=2,
        default_temperature=0.7,
        evaluation_status="verified",
        context_window=8192,
    )
    mock_model_repo.list_routing_candidates.return_value = [
        ModelRoutingRow(db_model_id=1, model=duplicate, priority_weight=100),
        ModelRoutingRow(db_model_id=99, model=duplicate, priority_weight=60),
    ]
    selector = ModelSelector(
        model_repository=mock_model_repo,
        health_repository=mock_health_repo,
        snapshot_repository=mock_snapshot_repo,
    )
    evaluation = PromptEvaluationResult(
        intent="general",
        complexity_score=0.2,
        requires_code=False,
        requires_reasoning=False,
        requires_tools=False,
        requires_json=False,
        estimated_tokens=200,
        keywords=[],
    )
    task = GatewayTask(
        prompt="hello",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=None,
        require_json=False,
        discovery_mode=True,
    )
    decision = selector.build_decision(task=task, intent=Intent.GENERAL, evaluation=evaluation)
    assert len(decision.scored_candidates) == 1
    assert decision.scored_candidates[0].model.model_id == "gpt-4"


def test_selector_applies_gap_decision_for_close_scores(
    monkeypatch: pytest.MonkeyPatch, mock_model_repo, mock_health_repo, mock_snapshot_repo
) -> None:
    premium = ModelProfile(
        model_id="premium/model",
        provider="openai",
        quality_score=7,
        latency_score=6,
        cost_score=4,
        default_temperature=0.2,
        capabilities={Capability.GENERAL, Capability.CODE, Capability.ANALYSIS},
        supports_tools=True,
        context_window=128000,
        tier="premium",
        evaluation_status="verified",
    )
    budget = ModelProfile(
        model_id="budget/model",
        provider="openrouter",
        quality_score=7,
        latency_score=7,
        cost_score=9,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
        supports_tools=False,
        context_window=32000,
        tier="budget",
        evaluation_status="cataloged",
    )
    mock_model_repo.list_routing_candidates.return_value = [
        ModelRoutingRow(db_model_id=1, model=budget, priority_weight=100),
        ModelRoutingRow(db_model_id=2, model=premium, priority_weight=100),
    ]

    def _fake_compute_model_score(**kwargs: object) -> ScoreBreakdown:
        model = kwargs["model"]
        if isinstance(model, ModelProfile) and model.model_id == "budget/model":
            return ScoreBreakdown(
                total=1.01,
                base_total=1.01,
                adjusted_total=1.01,
                model_score_adjustment=0.0,
                quality_component=0.3,
                latency_component=0.3,
                cost_component=0.3,
                priority_component=0.1,
                routing_bonus=0.0,
                use_case_bonus=0.0,
                provider_bonus=0.0,
                explanation="budget",
                capability_score=0.55,
                capability_confidence=0.8,
            )
        return ScoreBreakdown(
            total=1.00,
            base_total=1.00,
            adjusted_total=1.00,
            model_score_adjustment=0.0,
            quality_component=0.3,
            latency_component=0.3,
            cost_component=0.3,
            priority_component=0.1,
            routing_bonus=0.0,
            use_case_bonus=0.0,
            provider_bonus=0.0,
            explanation="premium",
            capability_score=0.90,
            capability_confidence=1.0,
        )

    monkeypatch.setattr(
        "packages.services.model_selection.service.compute_model_score",
        _fake_compute_model_score,
    )

    selector = ModelSelector(
        model_repository=mock_model_repo,
        health_repository=mock_health_repo,
        snapshot_repository=mock_snapshot_repo,
    )
    evaluation = PromptEvaluationResult(
        intent="general",
        complexity_score=0.3,
        requires_code=False,
        requires_reasoning=False,
        requires_tools=False,
        requires_json=False,
        estimated_tokens=120,
        keywords=[],
    )
    task = GatewayTask(
        prompt="route this prompt",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=None,
        require_json=False,
        discovery_mode=True,
    )
    decision = selector.build_decision(task=task, intent=Intent.GENERAL, evaluation=evaluation)
    assert decision.candidates[0].model_id == "premium/model"


def test_selector_near_tie_fallback_is_deterministic(
    monkeypatch: pytest.MonkeyPatch, mock_model_repo, mock_health_repo, mock_snapshot_repo
) -> None:
    model_a = ModelProfile(
        model_id="alpha/model",
        provider="openai",
        quality_score=7,
        latency_score=7,
        cost_score=7,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
        context_window=64000,
        tier="standard",
        evaluation_status="provisional",
    )
    model_b = ModelProfile(
        model_id="beta/model",
        provider="openai",
        quality_score=7,
        latency_score=7,
        cost_score=7,
        default_temperature=0.2,
        capabilities={Capability.GENERAL},
        context_window=64000,
        tier="standard",
        evaluation_status="provisional",
    )
    mock_model_repo.list_routing_candidates.return_value = [
        ModelRoutingRow(db_model_id=10, model=model_b, priority_weight=100),
        ModelRoutingRow(db_model_id=11, model=model_a, priority_weight=100),
    ]

    def _fake_equal_scores(**_kwargs: object) -> ScoreBreakdown:
        return ScoreBreakdown(
            total=1.0,
            base_total=1.0,
            adjusted_total=1.0,
            model_score_adjustment=0.0,
            quality_component=0.3,
            latency_component=0.3,
            cost_component=0.3,
            priority_component=0.1,
            routing_bonus=0.0,
            use_case_bonus=0.0,
            provider_bonus=0.0,
            explanation="equal",
            capability_score=0.8,
            capability_confidence=0.9,
        )

    monkeypatch.setattr(
        "packages.services.model_selection.service.compute_model_score",
        _fake_equal_scores,
    )

    selector = ModelSelector(
        model_repository=mock_model_repo,
        health_repository=mock_health_repo,
        snapshot_repository=mock_snapshot_repo,
    )
    evaluation = PromptEvaluationResult(
        intent="general",
        complexity_score=0.4,
        requires_code=False,
        requires_reasoning=False,
        requires_tools=False,
        requires_json=False,
        estimated_tokens=100,
        keywords=[],
    )
    task = GatewayTask(
        prompt="deterministic ordering check",
        priority=Priority.BALANCED,
        temperature=None,
        max_tokens=None,
        require_json=False,
        discovery_mode=True,
    )
    decision = selector.build_decision(task=task, intent=Intent.GENERAL, evaluation=evaluation)
    assert [candidate.model_id for candidate in decision.candidates] == ["alpha/model", "beta/model"]
