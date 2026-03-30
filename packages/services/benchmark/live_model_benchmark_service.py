"""Live (provider execution) benchmark: only path to `verified` catalog state.

Requires `OPENROUTER_API_KEY` and a model id that resolves to an OpenRouter model string.

Limitations (v1)
----------------
- Transport: OpenRouter Chat Completions only.
- Scope: text → text (same gate as heuristic screening).
- Tools case: if the upstream response has no `tool_calls`, the case fails (strict v1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from sqlmodel import Session, select

from packages.core.openrouter.pricing import compute_cost_score
from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.llm_model_routing_settings import LLMModelRoutingSettings
from packages.infrastructure.db.models.model_benchmark_run import (
    BenchmarkKind,
    BenchmarkRunStatus,
    BenchmarkScope,
    ModelBenchmarkRun,
)
from packages.infrastructure.providers.openrouter_client import ChatCompletionResult, OpenRouterClient, OpenRouterClientError
from packages.services.benchmark.model_benchmark_service import is_active_text_to_text_evaluation_scope

CURRENT_LIVE_VERSION = "benchmark-live-v1"

_MIN_TOOL_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_temperature",
            "description": "Get the current temperature for a city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City name"}},
                "required": ["city"],
            },
        },
    }
]


@runtime_checkable
class BenchmarkCompletionClient(Protocol):
    """Injectable client for tests (mock) or `OpenRouterClient` in production."""

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
        ...


def openrouter_api_model_id(model: LLMModel) -> str:
    """Map DB row to OpenRouter `model` parameter (e.g. `openai/gpt-4o-mini`)."""

    if model.openrouter_model_id:
        return model.openrouter_model_id.strip().lstrip("/")
    rk = (model.routing_key or "").strip()
    if rk.startswith("openrouter/"):
        return rk[len("openrouter/") :]
    return (model.external_model_id or "").strip()


def _latency_score_from_ms(ms: float) -> int:
    if ms <= 1_500:
        return 5
    if ms <= 4_000:
        return 4
    if ms <= 10_000:
        return 3
    if ms <= 20_000:
        return 2
    return 1


def _estimate_cost_usd(*, model: LLMModel, inp: int, out: int) -> float:
    pi = float(model.prompt_price or 0.0)
    co = float(model.completion_price or 0.0)
    return pi * float(inp) + co * float(out)


@dataclass
class _CaseResult:
    case_id: str
    ok: bool
    detail: str
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class LiveAggregate:
    quality_score: int
    latency_score: int
    cost_score: int
    json_reliability: float
    tool_reliability: float
    error_rate: float
    sample_size: int
    case_results: list[_CaseResult] = field(default_factory=list)


@dataclass(frozen=True)
class LiveBenchmarkOutcome:
    benchmark_run_id: int
    status: BenchmarkRunStatus
    passed: bool
    evaluation_status_after: ModelEvaluationStatus


class LiveModelBenchmarkService:
    def __init__(
        self,
        session: Session,
        *,
        completion_client: BenchmarkCompletionClient | None = None,
    ) -> None:
        self._session = session
        self._client = completion_client

    def _get_client(self) -> BenchmarkCompletionClient:
        if self._client is not None:
            return self._client
        settings = get_settings()
        return OpenRouterClient(
            base_url=settings.openrouter_base_url,
            timeout_seconds=max(120.0, settings.openrouter_fetch_timeout_seconds),
            http_referer=settings.openrouter_http_referer,
            api_key=settings.openrouter_api_key,
        )

    def run_live_benchmark_for_model(self, *, model_id: int) -> LiveBenchmarkOutcome:
        model = self._session.get(LLMModel, model_id)
        if model is None:
            raise ValueError(f"model id {model_id} not found")

        if model.evaluation_status == ModelEvaluationStatus.DEPRECATED:
            return self._skipped_outcome(
                model_id=model_id,
                model=model,
                summary="Live benchmark skipped: deprecated.",
                raw={"reason": "deprecated"},
            )

        if model.evaluation_status == ModelEvaluationStatus.CATALOGED:
            raise ValueError(
                "Run heuristic screening first; live benchmark requires at least `provisional` "
                "(or re-try from `rejected`)."
            )

        if not is_active_text_to_text_evaluation_scope(model):
            return self._skipped_outcome(
                model_id=model_id,
                model=model,
                summary="Live benchmark skipped: multimodal / out of text→text scope.",
                raw={"reason": "unsupported_modality"},
            )

        api_model = openrouter_api_model_id(model)
        if not api_model:
            raise ValueError("Cannot resolve OpenRouter model id for benchmark")

        client = self._get_client()
        cases: list[_CaseResult] = []

        cases.append(self._case_general(client=client, api_model=api_model, model=model))
        if model.supports_json:
            cases.append(self._case_json(client=client, api_model=api_model, model=model))
        if model.supports_tools:
            cases.append(self._case_tools(client=client, api_model=api_model, model=model))

        failed = [c for c in cases if not c.ok]
        error_rate = len(failed) / len(cases) if cases else 1.0
        passed = len(failed) == 0 and len(cases) > 0

        latencies = [float(c.latency_ms) for c in cases if c.latency_ms > 0]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        latency_score = _latency_score_from_ms(avg_lat)

        costs = [c.cost_usd for c in cases]
        avg_cost = sum(costs) / len(costs) if costs else 0.0
        cost_score = compute_cost_score(avg_cost)

        json_ok = all(c.ok for c in cases if c.case_id == "json_structured") or not model.supports_json
        tool_ok = all(c.ok for c in cases if c.case_id == "tool_call") or not model.supports_tools
        json_reliability = 1.0 if json_ok else 0.2
        tool_reliability = 1.0 if tool_ok else 0.2

        quality_score = 5 if passed else max(1, 5 - 2 * len(failed))

        aggregate = LiveAggregate(
            quality_score=min(5, quality_score),
            latency_score=latency_score,
            cost_score=cost_score,
            json_reliability=json_reliability,
            tool_reliability=tool_reliability,
            error_rate=error_rate,
            sample_size=len(cases),
            case_results=cases,
        )

        raw: dict[str, Any] = {
            "evaluation_version": CURRENT_LIVE_VERSION,
            "benchmark_kind": BenchmarkKind.LIVE.value,
            "benchmark_scope": BenchmarkScope.TEXT.value,
            "openrouter_model": api_model,
            "cases": [
                {
                    "id": c.case_id,
                    "ok": c.ok,
                    "detail": c.detail,
                    "latency_ms": c.latency_ms,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "cost_usd": c.cost_usd,
                }
                for c in cases
            ],
            "passed": passed,
        }

        bench_status = BenchmarkRunStatus.COMPLETED if passed else BenchmarkRunStatus.FAILED
        summary = (
            "Live benchmark passed; model is execution-verified."
            if passed
            else "Live benchmark failed one or more cases."
        )

        row = self._persist_live_run(
            model_id=model_id,
            status=bench_status,
            aggregate=aggregate,
            summary=summary,
            raw=raw,
        )
        self._session.flush()

        if passed:
            self._apply_live_pass(model=model, aggregate=aggregate)
        else:
            self._apply_live_fail(model=model)

        self._session.add(model)
        self._session.flush()

        return LiveBenchmarkOutcome(
            benchmark_run_id=row.id,  # type: ignore[arg-type]
            status=bench_status,
            passed=passed,
            evaluation_status_after=model.evaluation_status,
        )

    def _skipped_outcome(
        self,
        *,
        model_id: int,
        model: LLMModel,
        summary: str,
        raw: dict[str, Any],
    ) -> LiveBenchmarkOutcome:
        row = ModelBenchmarkRun(
            model_id=model_id,
            evaluation_version=CURRENT_LIVE_VERSION,
            benchmark_kind=BenchmarkKind.LIVE.value,
            benchmark_scope=BenchmarkScope.TEXT.value,
            status=BenchmarkRunStatus.SKIPPED_UNSUPPORTED.value,
            quality_score=0,
            latency_score=0,
            cost_score=0,
            json_reliability=0.0,
            tool_reliability=0.0,
            error_rate=0.0,
            sample_size=0,
            summary=summary,
            raw_results_json=raw,
        )
        self._session.add(row)
        self._session.flush()
        return LiveBenchmarkOutcome(
            benchmark_run_id=row.id,  # type: ignore[arg-type]
            status=BenchmarkRunStatus.SKIPPED_UNSUPPORTED,
            passed=False,
            evaluation_status_after=model.evaluation_status,
        )

    def _case_general(
        self,
        *,
        client: BenchmarkCompletionClient,
        api_model: str,
        model: LLMModel,
    ) -> _CaseResult:
        try:
            r = client.chat_completion(
                model=api_model,
                messages=[{"role": "user", "content": "Reply with exactly the token: PONG"}],
                max_tokens=32,
                temperature=0.0,
                response_format=None,
                tools=None,
                tool_choice=None,
            )
        except OpenRouterClientError as exc:
            return _CaseResult(case_id="general_text", ok=False, detail=str(exc))

        ok = "PONG" in r.content.upper().replace(" ", "")
        cost = _estimate_cost_usd(model=model, inp=r.input_tokens, out=r.output_tokens)
        return _CaseResult(
            case_id="general_text",
            ok=ok,
            detail="expected PONG in response" if not ok else "ok",
            latency_ms=r.latency_ms,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            cost_usd=cost,
        )

    def _case_json(
        self,
        *,
        client: BenchmarkCompletionClient,
        api_model: str,
        model: LLMModel,
    ) -> _CaseResult:
        try:
            r = client.chat_completion(
                model=api_model,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Return ONLY valid JSON (no markdown) with keys 'hello' (string) "
                            "and 'n' (number). Use hello=world and n=42."
                        ),
                    }
                ],
                max_tokens=128,
                temperature=0.0,
                response_format={"type": "json_object"},
                tools=None,
                tool_choice=None,
            )
        except OpenRouterClientError as exc:
            return _CaseResult(case_id="json_structured", ok=False, detail=str(exc))

        ok = False
        detail = "parse error"
        try:
            text = r.content.strip()
            data = json.loads(text)
            if isinstance(data, dict) and data.get("hello") == "world" and data.get("n") == 42:
                ok = True
                detail = "ok"
        except json.JSONDecodeError as exc:
            detail = f"json: {exc}"

        cost = _estimate_cost_usd(model=model, inp=r.input_tokens, out=r.output_tokens)
        return _CaseResult(
            case_id="json_structured",
            ok=ok,
            detail=detail,
            latency_ms=r.latency_ms,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            cost_usd=cost,
        )

    def _case_tools(
        self,
        *,
        client: BenchmarkCompletionClient,
        api_model: str,
        model: LLMModel,
    ) -> _CaseResult:
        try:
            r = client.chat_completion(
                model=api_model,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "You must call the function get_temperature with city='Paris'. "
                            "Do not answer with plain text only; use a tool call."
                        ),
                    }
                ],
                max_tokens=256,
                temperature=0.0,
                response_format=None,
                tools=_MIN_TOOL_SCHEMA,
                tool_choice="auto",
            )
        except OpenRouterClientError as exc:
            return _CaseResult(case_id="tool_call", ok=False, detail=str(exc))

        ok = bool(r.tool_calls)
        cost = _estimate_cost_usd(model=model, inp=r.input_tokens, out=r.output_tokens)
        return _CaseResult(
            case_id="tool_call",
            ok=ok,
            detail="tool_calls present" if ok else "no tool_calls in response",
            latency_ms=r.latency_ms,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            cost_usd=cost,
        )

    def _persist_live_run(
        self,
        *,
        model_id: int,
        status: BenchmarkRunStatus,
        aggregate: LiveAggregate,
        summary: str,
        raw: dict[str, Any],
    ) -> ModelBenchmarkRun:
        run = ModelBenchmarkRun(
            model_id=model_id,
            evaluation_version=CURRENT_LIVE_VERSION,
            benchmark_kind=BenchmarkKind.LIVE.value,
            benchmark_scope=BenchmarkScope.TEXT.value,
            status=status.value,
            quality_score=aggregate.quality_score,
            latency_score=aggregate.latency_score,
            cost_score=aggregate.cost_score,
            json_reliability=aggregate.json_reliability,
            tool_reliability=aggregate.tool_reliability,
            error_rate=aggregate.error_rate,
            sample_size=aggregate.sample_size,
            summary=summary,
            raw_results_json=raw,
        )
        self._session.add(run)
        return run

    def _apply_live_pass(self, *, model: LLMModel, aggregate: LiveAggregate) -> None:
        now = datetime.now(timezone.utc)
        model.evaluation_status = ModelEvaluationStatus.VERIFIED
        model.evaluation_confidence = 1.0
        model.last_evaluated_at = now
        model.evaluation_version = CURRENT_LIVE_VERSION

        assert model.id is not None
        stmt = select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == model.id)
        rs = self._session.exec(stmt).first()
        if rs is None:
            self._session.add(
                LLMModelRoutingSettings(
                    model_id=model.id,
                    quality_score=aggregate.quality_score,
                    latency_score=aggregate.latency_score,
                    cost_score=aggregate.cost_score,
                    default_temperature=0.2,
                    priority_weight=100,
                    allow_fallback=True,
                    enabled_for_routing=True,
                    is_evaluated_for_routing=True,
                )
            )
            return

        rs.quality_score = aggregate.quality_score
        rs.latency_score = aggregate.latency_score
        rs.cost_score = aggregate.cost_score
        rs.is_evaluated_for_routing = True
        rs.enabled_for_routing = True
        self._session.add(rs)

    def _apply_live_fail(self, *, model: LLMModel) -> None:
        now = datetime.now(timezone.utc)
        model.evaluation_status = ModelEvaluationStatus.REJECTED
        model.evaluation_confidence = 0.0
        model.last_evaluated_at = now
        model.evaluation_version = CURRENT_LIVE_VERSION

        assert model.id is not None
        stmt = select(LLMModelRoutingSettings).where(LLMModelRoutingSettings.model_id == model.id)
        rs = self._session.exec(stmt).first()
        if rs is None:
            self._session.add(
                LLMModelRoutingSettings(
                    model_id=model.id,
                    quality_score=0,
                    latency_score=0,
                    cost_score=0,
                    default_temperature=0.2,
                    priority_weight=100,
                    allow_fallback=True,
                    enabled_for_routing=False,
                    is_evaluated_for_routing=False,
                )
            )
            return
        rs.enabled_for_routing = False
        rs.is_evaluated_for_routing = False
        self._session.add(rs)
