from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies.orchestrator import get_db_session
from app.api.routes import gateway as gateway_module
from app.api.routes.gateway import router as gateway_router
from packages.domain.gateway import (
    GatewayExecutionResult,
    GatewayTask,
    Intent,
    ProviderResponse,
    RankingHighlight,
    RankingSummary,
    RoutingDecision,
    ScoredCandidate,
)
from packages.domain.models import Capability, ModelProfile


@pytest.fixture
def gateway_client_mock_orch() -> Generator[tuple[TestClient, MagicMock], None, None]:
    mock_orch = MagicMock()

    profile = ModelProfile(
        model_id="anthropic/claude-test",
        provider="anthropic",
        quality_score=4,
        latency_score=4,
        cost_score=4,
        default_temperature=0.3,
        capabilities={Capability.GENERAL},
        prompt_price=0.0000005,
        completion_price=0.0000015,
    )
    _h = RankingHighlight(
        model_id="anthropic/claude-test",
        display_name="Claude Test",
        provider="anthropic",
        reason_key="rankingReasonBestOverallBalanced",
    )
    _summary = RankingSummary(
        best_overall=_h,
        free_alternative=None,
        best_quality=_h,
        best_cost=_h,
        best_speed=_h,
    )
    result = GatewayExecutionResult(
        request_id=uuid4(),
        response=ProviderResponse(content="ok", provider="anthropic", model_id="anthropic/claude-test"),
        decision=RoutingDecision(
            intent=Intent.GENERAL,
            reason="test",
            applied_temperature=0.5,
            candidates=[profile],
            scored_candidates=(
                ScoredCandidate(
                    model=profile,
                    priority_weight=100,
                    db_model_id=1,
                    rank=1,
                    quality_score=4.0,
                    latency_score=4.0,
                    cost_score=4.0,
                    final_score=4.2,
                    model_score_adjustment=0.2,
                    explanation="score=4.2",
                    pros=(),
                    cons=(),
                ),
            ),
        ),
        attempts=[],
        fallback_used=False,
        ranking_summary=_summary,
    )
    mock_orch.execute.return_value = result

    def override_session() -> Generator[MagicMock, None, None]:
        yield MagicMock()

    app = FastAPI()
    app.include_router(gateway_router)
    app.dependency_overrides[get_db_session] = override_session

    with TestClient(app) as client:
        with patch.object(gateway_module, "get_gateway_orchestrator", return_value=mock_orch):
            yield client, mock_orch

    app.dependency_overrides.clear()


def test_advanced_completion_passes_options_and_returns_200(
    gateway_client_mock_orch: tuple[TestClient, MagicMock],
) -> None:
    client, mock_orch = gateway_client_mock_orch

    body = {
        "prompt": "hello world",
        "priority": "balanced",
        "use_cases": ["api", "ide"],
        "preferred_providers": ["anthropic"],
        "response_depth": "detailed",
    }
    r = client.post("/v1/chat/completions/advanced", json=body)

    assert r.status_code == 200
    mock_orch.execute.assert_called_once()
    task = mock_orch.execute.call_args[0][0]
    assert isinstance(task, GatewayTask)
    assert task.use_cases == ["api", "ide"]
    assert task.preferred_providers == ["anthropic"]
    assert task.response_depth == "detailed"
    body = r.json()
    assert body["ranking"]
    assert "model_score_adjustment" in body["ranking"][0]
    assert body["ranking"][0]["cost_per_million_input"] == pytest.approx(0.5)
    assert body["ranking"][0]["cost_per_million_output"] == pytest.approx(1.5)
