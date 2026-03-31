from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from packages.domain.gateway import Priority
from packages.domain.models import Capability
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.llm_model_capability import LLMModelCapability
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.model_benchmark_run import BenchmarkKind, BenchmarkRunStatus, BenchmarkScope, ModelBenchmarkRun
from packages.infrastructure.db.models.model_evaluation import ModelEvaluation
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.seed_types import SeededModelUpsertParams
from packages.infrastructure.db.models.provider import Provider
from packages.infrastructure.providers.openrouter_client import ChatCompletionResult, OpenRouterClientError
from packages.services.benchmark.live_model_benchmark_service import CURRENT_LIVE_VERSION, LiveModelBenchmarkService
from packages.services.benchmark.model_benchmark_service import (
    CURRENT_HEURISTIC_VERSION,
    ModelBenchmarkService,
    compute_deterministic_scores,
)


def _engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Provider.__table__.create(eng, checkfirst=True)
    LLMModel.__table__.create(eng, checkfirst=True)
    LLMModelCapability.__table__.create(eng, checkfirst=True)
    LLMModelRoutingSettings.__table__.create(eng, checkfirst=True)
    ModelBenchmarkRun.__table__.create(eng, checkfirst=True)
    return eng


def test_heuristic_pass_promotes_cataloged_to_provisional_and_does_not_enable_routing() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="gpt-good",
            routing_key="openrouter/openai/gpt-good",
            display_name="Good",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=True,
            supports_vision=False,
            tier="premium",
            context_window=128_000,
            max_output_tokens=4096,
            prompt_price=0.0,
            completion_price=0.0,
            input_modalities=["text"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.CATALOGED,
        )
        session.add(m)
        session.flush()
        session.add(
            LLMModelRoutingSettings(
                model_id=m.id,
                quality_score=0,
                latency_score=0,
                cost_score=0,
                enabled_for_routing=False,
                is_evaluated_for_routing=False,
            )
        )
        session.commit()

        svc = ModelBenchmarkService(session)
        out = svc.run_heuristic_screening(model_id=m.id)
        session.commit()

        assert out.passed is True
        assert out.status == BenchmarkRunStatus.COMPLETED
        assert out.evaluation_status_after == ModelEvaluationStatus.PROVISIONAL

        m2 = session.get(LLMModel, m.id)
        assert m2 is not None
        assert m2.evaluation_status == ModelEvaluationStatus.PROVISIONAL
        assert m2.evaluation_version == CURRENT_HEURISTIC_VERSION
        assert m2.last_evaluated_at is not None

        rs = session.exec(select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == m.id)).one()
        expected = compute_deterministic_scores(m2)
        assert rs.quality_score == expected.quality_score
        assert rs.latency_score == expected.latency_score
        assert rs.cost_score == expected.cost_score
        assert rs.is_evaluated_for_routing is False
        assert rs.enabled_for_routing is False

        runs = session.exec(select(ModelBenchmarkRun).where(ModelBenchmarkRun.model_id == m.id)).all()
        assert len(runs) == 1
        assert runs[0].status == BenchmarkRunStatus.COMPLETED.value
        assert runs[0].benchmark_kind == BenchmarkKind.HEURISTIC.value


def test_heuristic_fail_sets_rejected_and_disables_routing() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="xai", display_name="xAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="expensive",
            routing_key="openrouter/xai/expensive",
            display_name="Expensive",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=True,
            supports_vision=False,
            tier="premium",
            context_window=8_000,
            max_output_tokens=1024,
            prompt_price=0.001,
            completion_price=0.001,
            input_modalities=["text"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.CATALOGED,
        )
        session.add(m)
        session.flush()
        session.add(
            LLMModelRoutingSettings(
                model_id=m.id,
                quality_score=5,
                latency_score=5,
                cost_score=5,
                enabled_for_routing=True,
                is_evaluated_for_routing=True,
            )
        )
        session.commit()

        svc = ModelBenchmarkService(session)
        out = svc.run_heuristic_screening(model_id=m.id)
        session.commit()

        assert out.passed is False
        assert out.status == BenchmarkRunStatus.FAILED
        assert out.evaluation_status_after == ModelEvaluationStatus.REJECTED

        m2 = session.get(LLMModel, m.id)
        assert m2 is not None
        assert m2.evaluation_status == ModelEvaluationStatus.REJECTED

        rs = session.exec(select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == m.id)).one()
        assert rs.enabled_for_routing is False
        assert rs.is_evaluated_for_routing is False


def test_list_routing_candidates_requires_non_cataloged_status_even_if_evaluated_flags_set() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="p", display_name="P", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="m3",
            routing_key="openrouter/p/m3",
            display_name="M3",
            is_active=True,
            is_available=True,
            supports_json=False,
            supports_tools=False,
            supports_vision=False,
            tier="alternative",
            context_window=None,
            max_output_tokens=None,
            evaluation_status=ModelEvaluationStatus.CATALOGED,
        )
        session.add(m)
        session.flush()
        session.add(
            LLMModelRoutingSettings(
                model_id=m.id,
                quality_score=5,
                latency_score=5,
                cost_score=5,
                enabled_for_routing=True,
                is_evaluated_for_routing=True,
            )
        )
        session.commit()

        repo = ModelRepository(session)
        out = repo.list_routing_candidates(priority=Priority.BALANCED, require_json=False)
        assert out == []


def test_list_routing_includes_provisional_when_enabled_flags_true() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="p2", display_name="P2", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="m4",
            routing_key="openrouter/p2/m4",
            display_name="M4",
            is_active=True,
            is_available=True,
            supports_json=False,
            supports_tools=False,
            supports_vision=False,
            tier="alternative",
            context_window=None,
            max_output_tokens=None,
            evaluation_status=ModelEvaluationStatus.PROVISIONAL,
        )
        session.add(m)
        session.flush()
        session.add(
            LLMModelRoutingSettings(
                model_id=m.id,
                quality_score=5,
                latency_score=5,
                cost_score=5,
                enabled_for_routing=True,
                is_evaluated_for_routing=True,
            )
        )
        session.commit()

        repo = ModelRepository(session)
        out = repo.list_routing_candidates(priority=Priority.BALANCED, require_json=False)
        assert len(out) == 1
        assert out[0].model.model_id == "openrouter/p2/m4"


def test_seeded_upsert_marks_provisional_not_verified() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()
        assert p.id is not None

        repo = ModelRepository(session)
        _, row = repo.upsert_seeded_model(
            provider_id=p.id,
            params=SeededModelUpsertParams(
                source_provider="openai",
                external_model_id="gpt-4o",
                display_name="GPT-4o",
                supports_json=True,
                supports_tools=True,
                supports_vision=False,
                tier="premium",
                context_window=128_000,
                max_output_tokens=16_384,
                quality_score=5,
                latency_score=2,
                cost_score=1,
                capabilities=frozenset({Capability.GENERAL}),
            ),
        )
        session.commit()

        m = session.get(LLMModel, row.id)
        assert m is not None
        assert m.evaluation_status == ModelEvaluationStatus.PROVISIONAL
        assert m.evaluation_version == "seeded"
        assert m.last_evaluated_at is not None

        rs = session.exec(select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == row.id)).one()
        assert rs.enabled_for_routing is False
        assert rs.is_evaluated_for_routing is False


def test_benchmark_table_distinct_from_request_model_evaluations() -> None:
    assert ModelEvaluation.__tablename__ == "model_evaluations"
    assert ModelBenchmarkRun.__tablename__ == "model_benchmark_runs"
    assert ModelEvaluation.__table__.c.request_id is not None
    assert "request_id" not in ModelBenchmarkRun.__table__.c


class _FakeBenchClient:
    """Returns successful outcomes for general, JSON, and tool cases."""

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        response_format: dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
        tool_choice: str | object | None,
    ) -> ChatCompletionResult:
        _ = messages, max_tokens, temperature, tool_choice
        if response_format is not None and response_format.get("type") == "json_object":
            return ChatCompletionResult(
                content='{"hello":"world","n":42}',
                model=model,
                input_tokens=12,
                output_tokens=20,
                latency_ms=80,
                raw={},
            )
        if tools:
            return ChatCompletionResult(
                content="",
                model=model,
                input_tokens=15,
                output_tokens=5,
                latency_ms=120,
                raw={},
                tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "get_temperature", "arguments": "{}"}}],
            )
        return ChatCompletionResult(
            content="PONG",
            model=model,
            input_tokens=5,
            output_tokens=2,
            latency_ms=40,
            raw={},
        )


def test_live_benchmark_success_promotes_to_verified() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="gpt-4o-mini",
            routing_key="openrouter/openai/gpt-4o-mini",
            openrouter_model_id="openai/gpt-4o-mini",
            display_name="Mini",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=True,
            supports_vision=False,
            tier="premium",
            context_window=128_000,
            max_output_tokens=4096,
            prompt_price=0.0000001,
            completion_price=0.0000002,
            input_modalities=["text"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.PROVISIONAL,
        )
        session.add(m)
        session.flush()
        session.add(
            LLMModelRoutingSettings(
                model_id=m.id,
                quality_score=3,
                latency_score=3,
                cost_score=3,
                enabled_for_routing=False,
                is_evaluated_for_routing=False,
            )
        )
        session.commit()

        svc = LiveModelBenchmarkService(session, completion_client=_FakeBenchClient())
        out = svc.run_live_benchmark_for_model(model_id=m.id)
        session.commit()

        assert out.passed is True
        assert out.evaluation_status_after == ModelEvaluationStatus.VERIFIED

        m2 = session.get(LLMModel, m.id)
        assert m2 is not None
        assert m2.evaluation_status == ModelEvaluationStatus.VERIFIED
        assert m2.evaluation_version == CURRENT_LIVE_VERSION

        rs = session.exec(select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == m.id)).one()
        assert rs.enabled_for_routing is True
        assert rs.is_evaluated_for_routing is True

        runs = session.exec(
            select(ModelBenchmarkRun).where(
                ModelBenchmarkRun.model_id == m.id,
                ModelBenchmarkRun.benchmark_kind == BenchmarkKind.LIVE.value,
            )
        ).all()
        assert len(runs) == 1
        assert runs[0].sample_size == 3


def test_live_benchmark_failure_sets_rejected() -> None:
    class _BadClient:
        def chat_completion(
            self,
            *,
            model: str,
            messages: list[dict[str, Any]],
            max_tokens: int,
            temperature: float,
            response_format: dict[str, Any] | None,
            tools: list[dict[str, Any]] | None,
            tool_choice: str | object | None,
        ) -> ChatCompletionResult:
            _ = model, messages, max_tokens, temperature, response_format, tools, tool_choice
            return ChatCompletionResult(
                content="NOPE",
                model="x",
                input_tokens=1,
                output_tokens=1,
                latency_ms=10,
                raw={},
            )

    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="bad",
            routing_key="openrouter/openai/bad",
            openrouter_model_id="openai/bad",
            display_name="Bad",
            is_active=True,
            is_available=True,
            supports_json=False,
            supports_tools=False,
            supports_vision=False,
            tier="premium",
            context_window=8_000,
            max_output_tokens=1024,
            input_modalities=["text"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.PROVISIONAL,
        )
        session.add(m)
        session.flush()
        session.add(
            LLMModelRoutingSettings(
                model_id=m.id,
                quality_score=5,
                latency_score=5,
                cost_score=5,
                enabled_for_routing=True,
                is_evaluated_for_routing=True,
            )
        )
        session.commit()

        svc = LiveModelBenchmarkService(session, completion_client=_BadClient())
        out = svc.run_live_benchmark_for_model(model_id=m.id)
        session.commit()

        assert out.passed is False
        assert out.evaluation_status_after == ModelEvaluationStatus.REJECTED

        rs = session.exec(select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == m.id)).one()
        assert rs.enabled_for_routing is False
        assert rs.is_evaluated_for_routing is False


def test_live_benchmark_raises_when_model_still_cataloged() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="x",
            routing_key="openrouter/openai/x",
            openrouter_model_id="openai/x",
            display_name="X",
            is_active=True,
            is_available=True,
            supports_json=False,
            supports_tools=False,
            supports_vision=False,
            tier="premium",
            context_window=8_000,
            max_output_tokens=1024,
            input_modalities=["text"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.CATALOGED,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = LiveModelBenchmarkService(session, completion_client=_FakeBenchClient())
        with pytest.raises(ValueError, match="heuristic screening"):
            svc.run_live_benchmark_for_model(model_id=m.id)


def test_heuristic_evaluates_vision_model_in_text_scope() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="vision",
            routing_key="openrouter/openai/vision",
            display_name="Vision",
            is_active=True,
            is_available=True,
            supports_json=False,
            supports_tools=False,
            supports_vision=True,
            tier="premium",
            context_window=8_000,
            max_output_tokens=1024,
            input_modalities=["text", "image"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.CATALOGED,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = ModelBenchmarkService(session)
        out = svc.run_heuristic_screening(model_id=m.id)
        session.commit()

        assert out.passed is True
        assert out.status == BenchmarkRunStatus.COMPLETED
        m2 = session.get(LLMModel, m.id)
        assert m2 is not None
        assert m2.evaluation_status == ModelEvaluationStatus.PROVISIONAL
        run = session.exec(select(ModelBenchmarkRun).where(ModelBenchmarkRun.model_id == m.id)).one()
        assert run.benchmark_scope == BenchmarkScope.TEXT.value


def test_heuristic_evaluates_text_plus_file_image_model_in_text_scope() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="anthropic", display_name="Anthropic", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="multimodal-text",
            routing_key="openrouter/anthropic/multimodal-text",
            display_name="Multimodal Text",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=False,
            supports_vision=True,
            tier="premium",
            context_window=200_000,
            max_output_tokens=4096,
            input_modalities=["text", "image", "file"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.CATALOGED,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = ModelBenchmarkService(session)
        out = svc.run_heuristic_screening(model_id=m.id)
        session.commit()

        assert out.passed is True
        assert out.status == BenchmarkRunStatus.COMPLETED
        run = session.exec(select(ModelBenchmarkRun).where(ModelBenchmarkRun.model_id == m.id)).one()
        assert run.benchmark_scope == BenchmarkScope.TEXT.value


def test_heuristic_image_text_v2_promotes_to_provisional() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="vision-v2",
            routing_key="openrouter/openai/vision-v2",
            display_name="Vision V2",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=False,
            supports_vision=True,
            tier="premium",
            context_window=8_000,
            max_output_tokens=1024,
            input_modalities=["text", "image"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.CATALOGED,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = ModelBenchmarkService(session)
        out = svc.run_heuristic_screening(model_id=m.id, enable_image_text_v2=True)
        session.commit()

        assert out.passed is True
        assert out.status == BenchmarkRunStatus.COMPLETED
        m2 = session.get(LLMModel, m.id)
        assert m2 is not None
        assert m2.evaluation_status == ModelEvaluationStatus.PROVISIONAL
        run = session.exec(select(ModelBenchmarkRun).where(ModelBenchmarkRun.model_id == m.id)).one()
        assert run.benchmark_scope == BenchmarkScope.IMAGE_TO_TEXT.value


def test_live_image_text_v2_strict_uses_image_case_and_verifies() -> None:
    class _VisionClient:
        def chat_completion(
            self,
            *,
            model: str,
            messages: list[dict[str, Any]],
            max_tokens: int,
            temperature: float,
            response_format: dict[str, Any] | None,
            tools: list[dict[str, Any]] | None,
            tool_choice: str | object | None,
        ) -> ChatCompletionResult:
            _ = model, max_tokens, temperature, tools, tool_choice
            content = messages[0].get("content")
            if isinstance(content, list):
                return ChatCompletionResult(
                    content='{"label":"red_square","dominant_color":"red"}',
                    model="vision",
                    input_tokens=20,
                    output_tokens=16,
                    latency_ms=90,
                    raw={},
                )
            if response_format is not None and response_format.get("type") == "json_object":
                return ChatCompletionResult(
                    content='{"hello":"world","n":42}',
                    model="vision",
                    input_tokens=8,
                    output_tokens=8,
                    latency_ms=40,
                    raw={},
                )
            return ChatCompletionResult(
                content="PONG",
                model="vision",
                input_tokens=5,
                output_tokens=2,
                latency_ms=30,
                raw={},
            )

    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="vision-live-v2",
            routing_key="openrouter/openai/vision-live-v2",
            openrouter_model_id="openai/vision-live-v2",
            display_name="Vision Live V2",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=False,
            supports_vision=True,
            tier="premium",
            context_window=32_000,
            max_output_tokens=1024,
            input_modalities=["text", "image"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.PROVISIONAL,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = LiveModelBenchmarkService(session, completion_client=_VisionClient())
        out = svc.run_live_benchmark_for_model(
            model_id=m.id,
            enable_image_text_v2=True,
            strict_image_text_checks=True,
        )
        session.commit()

        assert out.passed is True
        assert out.evaluation_status_after == ModelEvaluationStatus.VERIFIED
        run = session.exec(
            select(ModelBenchmarkRun).where(
                ModelBenchmarkRun.model_id == m.id,
                ModelBenchmarkRun.benchmark_kind == BenchmarkKind.LIVE.value,
            )
        ).one()
        assert run.benchmark_scope == BenchmarkScope.IMAGE_TO_TEXT.value


def test_heuristic_file_text_v3_promotes_to_provisional() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="file-v3",
            routing_key="openrouter/openai/file-v3",
            display_name="File V3",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=False,
            supports_vision=False,
            tier="premium",
            context_window=8_000,
            max_output_tokens=1024,
            input_modalities=["text", "file"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.CATALOGED,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = ModelBenchmarkService(session)
        out = svc.run_heuristic_screening(model_id=m.id, enable_file_text_v3=True)
        session.commit()

        assert out.passed is True
        assert out.status == BenchmarkRunStatus.COMPLETED
        m2 = session.get(LLMModel, m.id)
        assert m2 is not None
        assert m2.evaluation_status == ModelEvaluationStatus.PROVISIONAL
        run = session.exec(select(ModelBenchmarkRun).where(ModelBenchmarkRun.model_id == m.id)).one()
        assert run.benchmark_scope == BenchmarkScope.FILE_TO_TEXT.value


def test_live_file_text_v3_strict_uses_txt_csv_cases_and_verifies() -> None:
    class _FileClient:
        def chat_completion(
            self,
            *,
            model: str,
            messages: list[dict[str, Any]],
            max_tokens: int,
            temperature: float,
            response_format: dict[str, Any] | None,
            tools: list[dict[str, Any]] | None,
            tool_choice: str | object | None,
        ) -> ChatCompletionResult:
            _ = model, max_tokens, temperature, response_format, tools, tool_choice
            content = messages[0].get("content")
            if isinstance(content, list):
                payload = json.dumps(content)
                if "sample.csv" in payload:
                    return ChatCompletionResult(
                        content='{"source_type":"csv","row_count":1}',
                        model="file",
                        input_tokens=16,
                        output_tokens=12,
                        latency_ms=70,
                        raw={},
                    )
                if "sample.txt" in payload:
                    return ChatCompletionResult(
                        content='{"source_type":"txt","contains_hello":true}',
                        model="file",
                        input_tokens=16,
                        output_tokens=12,
                        latency_ms=70,
                        raw={},
                    )
            return ChatCompletionResult(
                content="PONG",
                model="file",
                input_tokens=5,
                output_tokens=2,
                latency_ms=30,
                raw={},
            )

    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="file-live-v3",
            routing_key="openrouter/openai/file-live-v3",
            openrouter_model_id="openai/file-live-v3",
            display_name="File Live V3",
            is_active=True,
            is_available=True,
            supports_json=False,
            supports_tools=False,
            supports_vision=False,
            tier="premium",
            context_window=32_000,
            max_output_tokens=1024,
            input_modalities=["text", "file"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.PROVISIONAL,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = LiveModelBenchmarkService(session, completion_client=_FileClient())
        out = svc.run_live_benchmark_for_model(
            model_id=m.id,
            enable_file_text_v3=True,
            strict_file_text_checks=True,
        )
        session.commit()

        assert out.passed is True
        assert out.evaluation_status_after == ModelEvaluationStatus.VERIFIED
        run = session.exec(
            select(ModelBenchmarkRun).where(
                ModelBenchmarkRun.model_id == m.id,
                ModelBenchmarkRun.benchmark_kind == BenchmarkKind.LIVE.value,
            )
        ).one()
        assert run.benchmark_scope == BenchmarkScope.FILE_TO_TEXT.value


def test_live_non_chat_model_is_skipped_unsupported() -> None:
    class _NonChatClient:
        def chat_completion(
            self,
            *,
            model: str,
            messages: list[dict[str, Any]],
            max_tokens: int,
            temperature: float,
            response_format: dict[str, Any] | None,
            tools: list[dict[str, Any]] | None,
            tool_choice: str | object | None,
        ) -> ChatCompletionResult:
            _ = model, messages, max_tokens, temperature, response_format, tools, tool_choice
            raise OpenRouterClientError(
                "OpenRouter chat completion failed: 404 | detail: "
                "This is not a chat model and thus not supported in the v1/chat/completions endpoint. "
                "Did you mean to use v1/completions?"
            )

        def completion(
            self,
            *,
            model: str,
            prompt: str,
            max_tokens: int,
            temperature: float,
        ) -> ChatCompletionResult:
            _ = model, prompt, max_tokens, temperature
            return ChatCompletionResult(
                content="PONG",
                model="legacy-completions",
                input_tokens=4,
                output_tokens=2,
                latency_ms=20,
                raw={},
            )

    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="legacy-completions",
            routing_key="openrouter/openai/legacy-completions",
            openrouter_model_id="openai/legacy-completions",
            display_name="Legacy Completions",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=False,
            supports_vision=False,
            tier="premium",
            context_window=16_000,
            max_output_tokens=1024,
            input_modalities=["text"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.PROVISIONAL,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = LiveModelBenchmarkService(session, completion_client=_NonChatClient())
        out = svc.run_live_benchmark_for_model(model_id=m.id)
        session.commit()

        assert out.passed is False
        assert out.status == BenchmarkRunStatus.SKIPPED_UNSUPPORTED
        assert out.evaluation_status_after == ModelEvaluationStatus.PROVISIONAL
        run = session.exec(
            select(ModelBenchmarkRun).where(
                ModelBenchmarkRun.model_id == m.id,
                ModelBenchmarkRun.benchmark_kind == BenchmarkKind.LIVE.value,
            )
        ).one()
        assert run.status == BenchmarkRunStatus.SKIPPED_UNSUPPORTED.value
        assert run.summary.startswith("Live benchmark skipped:")
        raw = run.raw_results_json
        assert isinstance(raw, dict)
        probe = raw.get("completion_probe")
        assert isinstance(probe, dict)
        assert probe.get("ok") is True


def test_live_json_non_chat_like_error_does_not_force_skip_when_general_passes() -> None:
    class _MixedClient:
        def chat_completion(
            self,
            *,
            model: str,
            messages: list[dict[str, Any]],
            max_tokens: int,
            temperature: float,
            response_format: dict[str, Any] | None,
            tools: list[dict[str, Any]] | None,
            tool_choice: str | object | None,
        ) -> ChatCompletionResult:
            _ = model, messages, max_tokens, temperature, tools, tool_choice
            if response_format is not None and response_format.get("type") == "json_object":
                raise OpenRouterClientError(
                    "OpenRouter chat completion failed: 404 | detail: "
                    "This is not a chat model and thus not supported in the v1/chat/completions endpoint. "
                    "Did you mean to use v1/completions?"
                )
            return ChatCompletionResult(
                content="PONG",
                model="mixed",
                input_tokens=5,
                output_tokens=2,
                latency_ms=30,
                raw={},
            )

    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="google", display_name="Google", is_active=True)
        session.add(p)
        session.flush()

        m = LLMModel(
            provider_id=p.id,
            external_model_id="gemini-2.5-pro",
            routing_key="openrouter/google/gemini-2.5-pro",
            openrouter_model_id="google/gemini-2.5-pro",
            display_name="Gemini 2.5 Pro",
            is_active=True,
            is_available=True,
            supports_json=True,
            supports_tools=False,
            supports_vision=False,
            tier="premium",
            context_window=1_000_000,
            max_output_tokens=8192,
            input_modalities=["text"],
            output_modalities=["text"],
            evaluation_status=ModelEvaluationStatus.PROVISIONAL,
        )
        session.add(m)
        session.flush()
        session.commit()

        svc = LiveModelBenchmarkService(session, completion_client=_MixedClient())
        out = svc.run_live_benchmark_for_model(model_id=m.id)
        session.commit()

        assert out.status == BenchmarkRunStatus.FAILED
        run = session.exec(
            select(ModelBenchmarkRun).where(
                ModelBenchmarkRun.model_id == m.id,
                ModelBenchmarkRun.benchmark_kind == BenchmarkKind.LIVE.value,
            )
        ).one()
        assert run.status == BenchmarkRunStatus.FAILED.value
