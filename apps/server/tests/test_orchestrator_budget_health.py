from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from sqlmodel import Session
from packages.domain.gateway import GatewayTask, Priority, ScoredCandidate, HealthState, ModelTier
from packages.domain.models import ModelProfile
from packages.services.orchestration.orchestrator import GatewayOrchestrator
from packages.services.prompt_evaluation import PromptEvaluator
from packages.services.model_selection.service import ModelSelector
from packages.services.execution.fallback_executor import FallbackExecutor

def _make_model(model_id: str, prompt_price: float = 0.0, completion_price: float = 0.0) -> ModelProfile:
    return ModelProfile(
        model_id=model_id,
        provider="openai",
        quality_score=80,
        latency_score=70,
        cost_score=90,
        default_temperature=0.7,
        capabilities=set(),
        supports_tools=False,
        prompt_price=prompt_price,
        completion_price=completion_price,
    )

def _make_candidate(model: ModelProfile, rank: int, final_score: float = 1.0) -> ScoredCandidate:
    return ScoredCandidate(
        model=model,
        priority_weight=50,
        db_model_id=rank,
        rank=rank,
        quality_score=float(model.quality_score),
        latency_score=float(model.latency_score),
        cost_score=float(model.cost_score),
        final_score=final_score,
        model_score_adjustment=0.0,
        explanation="test",
        pros=(),
        cons=(),
        tier=ModelTier.TIER2_PROVISIONAL,
        health_status=HealthState.HEALTHY,
    )

class TestOrchestratorIntegration:
    @pytest.fixture
    def mock_deps(self):
        session = MagicMock(spec=Session)
        model_repo = MagicMock()
        fallback_registry = MagicMock()
        prompt_evaluator = MagicMock(spec=PromptEvaluator)
        selector = MagicMock(spec=ModelSelector)
        executor = MagicMock(spec=FallbackExecutor)
        
        # Mock request repo specifically since it's used in execute
        orchestrator = GatewayOrchestrator(
            session=session,
            model_repository=model_repo,
            fallback_registry=fallback_registry,
            prompt_evaluator=prompt_evaluator,
            selector=selector,
            executor=executor
        )
        # Patch internal repos to avoid DB calls
        orchestrator._request_repo = MagicMock()
        orchestrator._analysis_repo = MagicMock()
        orchestrator._eval_repo = MagicMock()
        orchestrator._execution_repo = MagicMock()
        orchestrator._attempt_repo = MagicMock()
        orchestrator._metrics_repo = MagicMock()
        orchestrator.model_repository.get_model_id_by_routing_key.return_value = 1
        orchestrator.model_repository.count_routing_ready_models.return_value = 1
        
        return orchestrator, prompt_evaluator, selector, executor

    def test_budget_filtering_integration(self, mock_deps):
        orchestrator, prompt_evaluator, selector, executor = mock_deps
        
        task = GatewayTask(
            prompt="test",
            priority=Priority.BALANCED,
            temperature=0.7,
            max_tokens=None,
            require_json=False,
            max_cost_usd=0.001
        )
        
        eval_res = MagicMock()
        eval_res.intent = "general"
        eval_res.complexity_score = 0.5
        eval_res.requires_code = False
        eval_res.requires_json = False
        eval_res.requires_tools = False
        eval_res.requires_reasoning = False
        eval_res.estimated_tokens = 1000
        eval_res.estimated_output_tokens = 512
        prompt_evaluator.evaluate.return_value = eval_res
        
        expensive_model = _make_model("expensive", prompt_price=0.1) # 1000 * 0.1 = 100 USD
        cheap_model = _make_model("cheap", prompt_price=0.0000001) # 1000 * 0.0000001 = 0.0001 USD
        
        candidates = (
            _make_candidate(expensive_model, 1, final_score=2.0),
            _make_candidate(cheap_model, 2, final_score=1.0),
        )
        
        decision = MagicMock()
        decision.scored_candidates = candidates
        decision.applied_temperature = 0.7
        decision.intent = "general"
        decision.candidates = [expensive_model, cheap_model]
        selector.build_decision.return_value = decision
        
        executor.run.return_value = MagicMock()
        executor.run.return_value.response.model_id = "cheap"
        
        orchestrator.execute(task)
        
        # Verify executor was called with ONLY the cheap model
        call_args = executor.run.call_args
        passed_decision = call_args.kwargs["decision"]
        assert len(passed_decision.scored_candidates) == 1
        assert passed_decision.scored_candidates[0].model.model_id == "cheap"

    def test_orchestrator_does_not_rescore_candidates(self, mock_deps):
        orchestrator, prompt_evaluator, selector, executor = mock_deps
        
        task = GatewayTask(
            prompt="test",
            priority=Priority.BALANCED,
            temperature=0.7,
            max_tokens=None,
            require_json=False
        )
        
        eval_res = MagicMock()
        eval_res.estimated_tokens = 10
        eval_res.estimated_output_tokens = 10
        eval_res.intent = "general"
        prompt_evaluator.evaluate.return_value = eval_res

        # Avoid MagicMock comparison issues in build_request_analysis_draft
        eval_res.complexity_score = 0.5
        
        model_a = _make_model("model-a")
        model_b = _make_model("model-b")
        
        # A is better than B normally
        candidates = (
            _make_candidate(model_a, 1, final_score=1.0),
            _make_candidate(model_b, 2, final_score=0.9),
        )
        
        decision = MagicMock()
        decision.scored_candidates = candidates
        decision.candidates = [model_a, model_b]
        selector.build_decision.return_value = decision
        
        executor.run.return_value = MagicMock()
        executor.run.return_value.response.model_id = "model-a"
        
        orchestrator.execute(task)
        
        passed_decision = executor.run.call_args.kwargs["decision"]
        assert passed_decision.scored_candidates[0].model.model_id == "model-a"
        assert passed_decision.scored_candidates[1].model.model_id == "model-b"
