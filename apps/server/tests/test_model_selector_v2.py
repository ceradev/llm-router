from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from packages.domain.gateway import GatewayTask, Intent, ModelTier, Priority
from packages.domain.models import ModelProfile
from packages.infrastructure.db.repositories.model_repository import ModelRepository, ModelRoutingRow
from packages.infrastructure.db.repositories.health_repository import HealthRepository
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotRepository
from packages.services.model_selection.service import ModelSelector
from packages.services.prompt_evaluation.types import PromptEvaluationResult

@pytest.fixture
def mock_model_repo():
    repo = MagicMock(spec=ModelRepository)
    # Model 1: Verified (Tier 1)
    m1 = ModelProfile(
        model_id="gpt-4", provider="openai", 
        quality_score=5, latency_score=3, cost_score=2, 
        default_temperature=0.7, evaluation_status="verified"
    )
    # Model 2: Cataloged (Tier 2)
    m2 = ModelProfile(
        model_id="llama-3", provider="meta", 
        quality_score=4, latency_score=4, cost_score=4, 
        default_temperature=0.7, evaluation_status="cataloged"
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

from packages.services.model_selection.snapshot_scoring import SnapshotAdjustedScores
from packages.infrastructure.db.repositories.snapshot_repository import SnapshotData
from datetime import datetime, timezone

def test_model_selector_snapshot_adjustments(mock_model_repo, mock_health_repo, mock_snapshot_repo):
    # Setup: Model 2 (llama-3, id=2) has a snapshot with slow latency
    # llama-3 base latency_score is 4. 
    # Snapshot p50 = 2500ms -> _latency_bucket returns -1.0.
    # Adjusted latency = 4.0 - 1.0 = 3.0.
    snapshot = SnapshotData(
        model_id=2, p50_latency_ms=2500.0, p95_latency_ms=4000.0,
        avg_cost_per_1k_tokens=0.002, success_rate_7d=0.95,
        sample_size=100, recorded_at=datetime.now(timezone.utc)
    )
    
    def get_snap(model_id):
        if model_id == 2: return snapshot
        return None
        
    mock_snapshot_repo.get_latest_snapshot.side_effect = get_snap
    
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
    
    task = GatewayTask(
        prompt="hello", priority=Priority.BALANCED, 
        temperature=None, max_tokens=None, require_json=False,
        discovery_mode=True
    )
    
    decision = selector.build_decision(
        task=task, intent=Intent.GENERAL, evaluation=evaluation
    )
    
    # Find llama-3 in scored candidates
    llama = next(c for c in decision.scored_candidates if c.model.model_id == "llama-3")
    
    # Verify snapshot data was passed to ScoredCandidate
    assert llama.snapshot_latency_p50 == 2500.0
    # Note: ScoredCandidate.latency_score currently reflects base profile (4.0) 
    # because we passed row.model to ScoredCandidate, but the final_score 
    # used the adjusted profile.
