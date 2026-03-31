from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from packages.infrastructure.config.settings import Settings
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.model_benchmark_run import (
    BenchmarkKind,
    BenchmarkRunStatus,
    ModelBenchmarkRun,
)
from packages.infrastructure.db.models.provider import Provider
from packages.infrastructure.providers.openrouter_client import ChatCompletionResult
from packages.services.benchmark.catalog_evaluation_orchestrator import (
    CatalogEvaluationConfig,
    CatalogEvaluationOrchestrator,
    catalog_evaluation_config_from_settings,
)
from packages.services.benchmark.live_model_benchmark_service import CURRENT_LIVE_VERSION, LiveModelBenchmarkService
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService


def _engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Provider.__table__.create(eng, checkfirst=True)
    LLMModel.__table__.create(eng, checkfirst=True)
    LLMModelRoutingSettings.__table__.create(eng, checkfirst=True)
    ModelBenchmarkRun.__table__.create(eng, checkfirst=True)
    return eng


def _add_cataloged_text_model(
    session: Session,
    *,
    provider: Provider,
    slug_suffix: str,
    routing_key: str,
    supports_vision: bool = False,
    input_modalities: list[str] | None = None,
    output_modalities: list[str] | None = None,
) -> LLMModel:
    m = LLMModel(
        provider_id=provider.id,
        external_model_id=slug_suffix,
        routing_key=routing_key,
        openrouter_model_id=routing_key.replace("openrouter/", ""),
        display_name=slug_suffix,
        is_active=True,
        is_available=True,
        supports_json=True,
        supports_tools=True,
        supports_vision=supports_vision,
        tier="premium",
        context_window=128_000,
        max_output_tokens=4096,
        prompt_price=0.0,
        completion_price=0.0,
        input_modalities=input_modalities or ["text"],
        output_modalities=output_modalities or ["text"],
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
    return m


class _FakeBenchClient:
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


def test_heuristic_phase_respects_max_models_per_run() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()
        _add_cataloged_text_model(session, provider=p, slug_suffix="a", routing_key="openrouter/openai/a")
        _add_cataloged_text_model(session, provider=p, slug_suffix="b", routing_key="openrouter/openai/b")
        _add_cataloged_text_model(session, provider=p, slug_suffix="c", routing_key="openrouter/openai/c")
        session.commit()

        orch = CatalogEvaluationOrchestrator(session)
        summary = orch.run(
            CatalogEvaluationConfig(max_models_per_run=2, max_live_benchmarks_per_run=0, provider_allowlist=None)
        )
        session.commit()

        assert summary.heuristic_attempted == 2
        heur_runs = session.exec(
            select(ModelBenchmarkRun).where(ModelBenchmarkRun.benchmark_kind == BenchmarkKind.HEURISTIC.value)
        ).all()
        assert len(heur_runs) == 2


def test_heuristic_includes_vision_model_in_text_scope() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()
        vision = _add_cataloged_text_model(
            session,
            provider=p,
            slug_suffix="vision",
            routing_key="openrouter/openai/vision",
            supports_vision=True,
        )
        session.commit()

        orch = CatalogEvaluationOrchestrator(session)
        summary = orch.run(
            CatalogEvaluationConfig(max_models_per_run=10, max_live_benchmarks_per_run=0, provider_allowlist=None)
        )
        session.commit()

        assert summary.heuristic_attempted == 1
        assert summary.heuristic_skipped_out_of_scope == 0
        n = session.exec(
            select(ModelBenchmarkRun).where(ModelBenchmarkRun.model_id == vision.id)
        ).all()
        assert len(n) == 1
        assert n[0].status == BenchmarkRunStatus.COMPLETED.value


def test_heuristic_phase_includes_rejected_models() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()
        m = _add_cataloged_text_model(
            session, provider=p, slug_suffix="rej", routing_key="openrouter/openai/rej"
        )
        m.evaluation_status = ModelEvaluationStatus.REJECTED
        session.add(m)
        session.commit()

        orch = CatalogEvaluationOrchestrator(session)
        summary = orch.run(
            CatalogEvaluationConfig(max_models_per_run=10, max_live_benchmarks_per_run=0, provider_allowlist=None)
        )
        session.commit()

        assert summary.heuristic_attempted == 1
        runs = session.exec(
            select(ModelBenchmarkRun).where(ModelBenchmarkRun.model_id == m.id)
        ).all()
        assert len(runs) == 1


def test_live_phase_respects_max_live_and_uses_mock_client() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()

        def _prov(mid: str, rk: str) -> None:
            m = LLMModel(
                provider_id=p.id,
                external_model_id=mid,
                routing_key=rk,
                openrouter_model_id=rk.replace("openrouter/", ""),
                display_name=mid,
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

        _prov("one", "openrouter/openai/one")
        _prov("two", "openrouter/openai/two")
        session.commit()

        live_svc = LiveModelBenchmarkService(session, completion_client=_FakeBenchClient())
        orch = CatalogEvaluationOrchestrator(session, live=live_svc)
        summary = orch.run(
            CatalogEvaluationConfig(max_models_per_run=0, max_live_benchmarks_per_run=1, provider_allowlist=None)
        )
        session.commit()

        assert summary.live_attempted == 1
        live_runs = session.exec(
            select(ModelBenchmarkRun).where(ModelBenchmarkRun.benchmark_kind == BenchmarkKind.LIVE.value)
        ).all()
        assert len(live_runs) == 1
        verified = session.exec(
            select(LLMModel).where(LLMModel.evaluation_status == ModelEvaluationStatus.VERIFIED)
        ).all()
        assert len(verified) == 1


def test_live_skips_verified_unless_include_flag() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()
        m = LLMModel(
            provider_id=p.id,
            external_model_id="v",
            routing_key="openrouter/openai/v",
            openrouter_model_id="openai/v",
            display_name="v",
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
            evaluation_status=ModelEvaluationStatus.VERIFIED,
            evaluation_version=CURRENT_LIVE_VERSION,
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

        live_svc = LiveModelBenchmarkService(session, completion_client=_FakeBenchClient())
        orch = CatalogEvaluationOrchestrator(session, live=live_svc)
        summary = orch.run(
            CatalogEvaluationConfig(
                max_models_per_run=0,
                max_live_benchmarks_per_run=5,
                provider_allowlist=None,
                include_verified_live=False,
            )
        )
        session.commit()

        assert summary.live_attempted == 0

        summary2 = orch.run(
            CatalogEvaluationConfig(
                max_models_per_run=0,
                max_live_benchmarks_per_run=5,
                provider_allowlist=None,
                include_verified_live=True,
            )
        )
        session.commit()
        assert summary2.live_attempted == 1


def test_provider_allowlist_filters_models() -> None:
    engine = _engine()
    with Session(engine) as session:
        pa = Provider(slug="openai", display_name="OpenAI", is_active=True)
        pb = Provider(slug="anthropic", display_name="Anthropic", is_active=True)
        session.add(pa)
        session.add(pb)
        session.flush()
        _add_cataloged_text_model(session, provider=pa, slug_suffix="oa", routing_key="openrouter/openai/oa")
        _add_cataloged_text_model(session, provider=pb, slug_suffix="ab", routing_key="openrouter/anthropic/ab")
        session.commit()

        orch = CatalogEvaluationOrchestrator(session)
        summary = orch.run(
            CatalogEvaluationConfig(
                max_models_per_run=10,
                max_live_benchmarks_per_run=0,
                provider_allowlist=frozenset({"openai"}),
            )
        )
        session.commit()

        assert summary.heuristic_attempted == 1
        runs = session.exec(
            select(ModelBenchmarkRun).where(ModelBenchmarkRun.benchmark_kind == BenchmarkKind.HEURISTIC.value)
        ).all()
        assert len(runs) == 1


def test_catalog_evaluation_config_from_settings_parses_allowlist() -> None:
    s = Settings(catalog_evaluation_provider_allowlist=" OpenAI , anthropic ")
    cfg = catalog_evaluation_config_from_settings(s)
    assert cfg.provider_allowlist == frozenset({"openai", "anthropic"})


def test_catalog_evaluation_config_includes_file_text_flags() -> None:
    s = Settings(
        catalog_evaluation_enable_file_text_v3=True,
        catalog_evaluation_strict_file_text_checks=False,
    )
    cfg = catalog_evaluation_config_from_settings(s)
    assert cfg.enable_file_text_v3 is True
    assert cfg.strict_file_text_checks is False


def test_heuristic_file_text_v3_runs_when_enabled() -> None:
    engine = _engine()
    with Session(engine) as session:
        p = Provider(slug="openai", display_name="OpenAI", is_active=True)
        session.add(p)
        session.flush()
        _add_cataloged_text_model(
            session,
            provider=p,
            slug_suffix="file-v3",
            routing_key="openrouter/openai/file-v3",
            supports_vision=False,
            input_modalities=["text", "file"],
            output_modalities=["text"],
        )
        session.commit()

        orch = CatalogEvaluationOrchestrator(session)
        summary = orch.run(
            CatalogEvaluationConfig(
                max_models_per_run=10,
                max_live_benchmarks_per_run=0,
                provider_allowlist=None,
                enable_file_text_v3=True,
            )
        )
        session.commit()

        assert summary.heuristic_attempted == 1
        run = session.exec(select(ModelBenchmarkRun).where(ModelBenchmarkRun.benchmark_kind == BenchmarkKind.HEURISTIC.value)).one()
        assert run.benchmark_scope == "file_to_text"


def test_sync_invokes_catalog_eval_when_enabled_and_survives_orchestrator_error() -> None:
    engine = _engine()
    raw_model = {
        "id": "openai/gpt-4o-mini",
        "name": "Mini",
        "pricing": {"prompt": "0.00000015", "completion": "0.00000060"},
        "context_length": 128000,
        "architecture": {"modality": "text", "input_modalities": ["text"], "output_modalities": ["text"]},
        "top_provider": {"max_completion_tokens": 4096},
    }

    settings = Settings(
        catalog_evaluation_after_openrouter_sync=True,
        catalog_evaluation_max_models_per_run=5,
        catalog_evaluation_max_live_per_run=2,
    )

    with Session(engine) as session:
        with patch("packages.services.sync.openrouter_sync_service.get_settings", return_value=settings):
            svc = OpenRouterSyncService(session)
            svc._client.fetch_models = lambda: [raw_model]  # type: ignore[method-assign]

            with patch(
                "packages.services.sync.openrouter_sync_service.CatalogEvaluationOrchestrator"
            ) as mock_orch_cls:
                mock_orch = MagicMock()
                mock_orch.run.side_effect = RuntimeError("orchestrator boom")
                mock_orch_cls.return_value = mock_orch

                out = svc.sync_models()

            assert out.models_processed == 1
            assert out.failures == []
            mock_orch_cls.assert_called_once()
            mock_orch.run.assert_called_once()
