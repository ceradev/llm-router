from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.dependencies.orchestrator import get_db_session
from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.db.models.llm_model import LLMModel, ModelEvaluationStatus
from packages.infrastructure.db.models.model_benchmark_run import ModelBenchmarkRun
from packages.infrastructure.db.models.provider import Provider
from packages.infrastructure.db.repositories.feedback_repository import FeedbackRepository
from packages.infrastructure.db.repositories.metrics_repository import MetricsRepository
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.repositories.request_repository import RequestRepository
from packages.services.benchmark.live_model_benchmark_service import LiveModelBenchmarkService
from packages.services.benchmark.model_benchmark_service import ModelBenchmarkService
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService


def get_admin_api_key() -> str | None:
    return get_settings().admin_api_key


def require_admin_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
    admin_api_key: Annotated[str | None, Depends(get_admin_api_key)] = None,
) -> None:
    if not admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured",
        )
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Key required",
        )
    if x_admin_key != admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )


router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)


class AdminDashboardResponse(BaseModel):
    total_models: int
    total_providers: int
    requests_today: int
    success_rate: float


class AdminModelListItem(BaseModel):
    routing_key: str
    display_name: str
    provider: str
    tier: str
    is_available: bool
    supports_json: bool
    supports_tools: bool
    supports_vision: bool
    input_modalities: list[str]
    output_modalities: list[str]
    evaluation_status: str


class AdminModelDetailResponse(BaseModel):
    routing_key: str
    display_name: str
    provider: str
    tier: str
    is_available: bool
    supports_vision: bool
    input_modalities: list[str]
    output_modalities: list[str]
    evaluation_status: str
    selected_count: int
    average_rating: float | None
    rating_count: int


class AdminRequestListItem(BaseModel):
    id: str
    prompt: str
    selected_model: str | None
    status: Literal["success", "fallback", "error", "pending"]
    created_at: str


class AdminRequestListResponse(BaseModel):
    date: str
    limit: int
    items: list[AdminRequestListItem]


class AdminSyncRunResponse(BaseModel):
    models_processed: int
    models_created: int
    models_updated: int


class AdminMetricsSummaryResponse(BaseModel):
    days: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_latency_ms: float
    unique_sessions_peak: int


class AdminModelEvaluationResponse(BaseModel):
    routing_key: str
    mode: Literal["heuristic", "live"]
    benchmark_run_id: int
    benchmark_status: str
    benchmark_scope: str
    passed: bool
    evaluation_status_after: str
    skip_reason: str | None = None
    cases: list[dict]


class AdminBatchEvaluationResponse(BaseModel):
    mode: Literal["heuristic", "live"]
    matched_models: int
    processed_models: int
    succeeded: int
    failed: int
    skipped: int
    benchmark_status_counts: dict[str, int]
    skip_reason_counts: dict[str, int] = {}
    skipped_models: list[dict[str, str]] = []
    failed_reason_counts: dict[str, int] = {}
    failed_models: list[dict[str, str]] = []
    error_messages: list[str]


def _run_single_batch_eval(
    *,
    session: Session,
    mode: Literal["heuristic", "live"],
    model: LLMModel,
    heuristic_service: ModelBenchmarkService,
    live_service: LiveModelBenchmarkService,
    enable_image_text_v2: bool,
    strict_image_text_checks: bool,
    enable_file_text_v3: bool,
    strict_file_text_checks: bool,
) -> tuple[str | None, str | None, str | None]:
    if model.id is None:
        return None, None, None
    if mode == "live":
        out = live_service.run_live_benchmark_for_model(
            model_id=model.id,
            enable_image_text_v2=enable_image_text_v2,
            strict_image_text_checks=strict_image_text_checks,
            enable_file_text_v3=enable_file_text_v3,
            strict_file_text_checks=strict_file_text_checks,
        )
    else:
        out = heuristic_service.run_heuristic_screening(
            model_id=model.id,
            enable_image_text_v2=enable_image_text_v2,
            enable_file_text_v3=enable_file_text_v3,
        )
    reason: str | None = None
    failed_reason: str | None = None
    run_row = session.get(ModelBenchmarkRun, out.benchmark_run_id)
    raw = run_row.raw_results_json if run_row and isinstance(run_row.raw_results_json, dict) else {}
    if out.status.value == "skipped_unsupported":
        raw_reason = raw.get("reason")
        if isinstance(raw_reason, str):
            reason = raw_reason
    elif out.status.value == "failed":
        cases = raw.get("cases")
        if isinstance(cases, list):
            for case in cases:
                if not isinstance(case, dict):
                    continue
                if case.get("ok") is True:
                    continue
                detail = str(case.get("detail") or "").lower()
                case_id = str(case.get("id") or "unknown")
                if "401 unauthorized" in detail or "user not found" in detail:
                    failed_reason = f"{case_id}:provider_auth"
                elif "404 not found" in detail and "not a chat model" in detail:
                    failed_reason = f"{case_id}:non_chat_model"
                elif "json" in detail:
                    failed_reason = f"{case_id}:json_validation"
                else:
                    failed_reason = f"{case_id}:execution_failure"
                break
        if failed_reason is None:
            failed_reason = "unknown_failure"
    return out.status.value, reason, failed_reason


def _request_status_from_row(*, fallback_used: bool, selected_model_id: int | None) -> str:
    if fallback_used:
        return "fallback"
    if selected_model_id is not None:
        return "success"
    return "pending"


@router.get("/dashboard")
def get_admin_dashboard(
    session: Annotated[Session, Depends(get_db_session)],
) -> AdminDashboardResponse:
    model_repo = ModelRepository(session)
    metrics_repo = MetricsRepository(session)
    request_repo = RequestRepository(session)

    total_models = model_repo.count_llm_models()
    providers_stmt = select(func.count(Provider.id)).where(Provider.is_active.is_(True))
    total_providers = int(session.exec(providers_stmt).one())
    today = date.today()
    daily = metrics_repo.get_daily(today)

    requests_today = request_repo.count_requests_for_date(target_date=today)
    if daily is None or daily.total_requests == 0:
        success_rate = 0.0
    else:
        success_rate = round(daily.successful_requests / max(daily.total_requests, 1), 3)

    return AdminDashboardResponse(
        total_models=total_models,
        total_providers=total_providers,
        requests_today=requests_today,
        success_rate=success_rate,
    )


@router.get("/models")
def list_admin_models(
    session: Annotated[Session, Depends(get_db_session)],
    provider: str | None = None,
    tier: str | None = None,
    available: bool | None = None,
    evaluation_status: str | None = None,
) -> list[AdminModelListItem]:
    rows = ModelRepository(session).list_models_for_admin(
        provider_slug=provider,
        tier=tier,
        is_available=available,
        evaluation_status=evaluation_status,
    )
    return [
        AdminModelListItem(
            routing_key=row.llm_model.routing_key,
            display_name=row.llm_model.display_name,
            provider=row.provider.slug,
            tier=row.llm_model.tier,
            is_available=row.llm_model.is_available,
            supports_json=row.llm_model.supports_json,
            supports_tools=row.llm_model.supports_tools,
            supports_vision=row.llm_model.supports_vision,
            input_modalities=list(row.llm_model.input_modalities or []),
            output_modalities=list(row.llm_model.output_modalities or []),
            evaluation_status=row.llm_model.evaluation_status.value,
        )
        for row in rows
    ]


@router.get("/models/{routing_key:path}")
def get_admin_model_detail(
    routing_key: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> AdminModelDetailResponse:
    model_repo = ModelRepository(session)
    request_repo = RequestRepository(session)
    feedback_repo = FeedbackRepository(session)

    row = model_repo.get_model_with_provider_by_routing_key(routing_key=routing_key)
    if row is None or row.llm_model.id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    selected_count = request_repo.count_selected_by_model_id(model_id=row.llm_model.id)
    avg_rating, rating_count = feedback_repo.get_model_feedback_stats(model_id=row.llm_model.id)
    return AdminModelDetailResponse(
        routing_key=row.llm_model.routing_key,
        display_name=row.llm_model.display_name,
        provider=row.provider.slug,
        tier=row.llm_model.tier,
        is_available=row.llm_model.is_available,
        supports_vision=row.llm_model.supports_vision,
        input_modalities=list(row.llm_model.input_modalities or []),
        output_modalities=list(row.llm_model.output_modalities or []),
        evaluation_status=row.llm_model.evaluation_status.value,
        selected_count=selected_count,
        average_rating=round(avg_rating, 2) if avg_rating is not None else None,
        rating_count=rating_count,
    )


@router.post("/models/{routing_key:path}/evaluate")
def run_admin_model_evaluation(
    routing_key: str,
    session: Annotated[Session, Depends(get_db_session)],
    mode: Annotated[Literal["heuristic", "live"], Query()] = "heuristic",
    enable_image_text_v2: Annotated[bool, Query()] = False,
    strict_image_text_checks: Annotated[bool, Query()] = True,
    enable_file_text_v3: Annotated[bool, Query()] = False,
    strict_file_text_checks: Annotated[bool, Query()] = True,
) -> AdminModelEvaluationResponse:
    model_row = ModelRepository(session).get_model_with_provider_by_routing_key(routing_key=routing_key)
    if model_row is None or model_row.llm_model.id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    try:
        if mode == "live":
            out = LiveModelBenchmarkService(session).run_live_benchmark_for_model(
                model_id=model_row.llm_model.id,
                enable_image_text_v2=enable_image_text_v2,
                strict_image_text_checks=strict_image_text_checks,
                enable_file_text_v3=enable_file_text_v3,
                strict_file_text_checks=strict_file_text_checks,
            )
        else:
            out = ModelBenchmarkService(session).run_heuristic_screening(
                model_id=model_row.llm_model.id,
                enable_image_text_v2=enable_image_text_v2,
                enable_file_text_v3=enable_file_text_v3,
            )
        session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    run_row = session.get(ModelBenchmarkRun, out.benchmark_run_id)
    if run_row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Benchmark run not found")
    raw = run_row.raw_results_json if isinstance(run_row.raw_results_json, dict) else {}
    cases = raw.get("cases")
    skip_reason = raw.get("reason")

    return AdminModelEvaluationResponse(
        routing_key=routing_key,
        mode=mode,
        benchmark_run_id=out.benchmark_run_id,
        benchmark_status=out.status.value,
        benchmark_scope=run_row.benchmark_scope,
        passed=out.passed,
        evaluation_status_after=out.evaluation_status_after.value,
        skip_reason=skip_reason if isinstance(skip_reason, str) else None,
        cases=cases if isinstance(cases, list) else [],
    )


@router.post("/models/evaluate-batch")
def run_admin_model_evaluation_batch(
    session: Annotated[Session, Depends(get_db_session)],
    mode: Annotated[Literal["heuristic", "live"], Query()] = "heuristic",
    provider: str | None = None,
    evaluation_status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 50,
    enable_image_text_v2: Annotated[bool, Query()] = False,
    strict_image_text_checks: Annotated[bool, Query()] = True,
    enable_file_text_v3: Annotated[bool, Query()] = False,
    strict_file_text_checks: Annotated[bool, Query()] = True,
) -> AdminBatchEvaluationResponse:
    stmt = (
        select(LLMModel, Provider)
        .join(Provider, Provider.id == LLMModel.provider_id)
        .where(LLMModel.is_active.is_(True))
        .where(Provider.is_active.is_(True))
        .order_by(LLMModel.id)
    )
    if provider:
        stmt = stmt.where(Provider.slug == provider)
    if evaluation_status:
        try:
            status_filter = ModelEvaluationStatus(evaluation_status.strip().lower())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid evaluation_status") from exc
        stmt = stmt.where(LLMModel.evaluation_status == status_filter)

    rows = session.exec(stmt).all()
    selected_rows = rows[:limit]
    succeeded = 0
    failed = 0
    skipped = 0
    status_counts: dict[str, int] = {}
    skip_reason_counts: dict[str, int] = {}
    skipped_models: list[dict[str, str]] = []
    failed_reason_counts: dict[str, int] = {}
    failed_models: list[dict[str, str]] = []
    errors: list[str] = []

    heuristic_service = ModelBenchmarkService(session)
    live_service = LiveModelBenchmarkService(session)

    for model, _provider in selected_rows:
        try:
            key, reason, failed_reason = _run_single_batch_eval(
                session=session,
                mode=mode,
                model=model,
                heuristic_service=heuristic_service,
                live_service=live_service,
                enable_image_text_v2=enable_image_text_v2,
                strict_image_text_checks=strict_image_text_checks,
                enable_file_text_v3=enable_file_text_v3,
                strict_file_text_checks=strict_file_text_checks,
            )
            if key is None:
                continue
            status_counts[key] = status_counts.get(key, 0) + 1
            if key == "completed":
                succeeded += 1
            elif key == "failed":
                failed += 1
                if failed_reason:
                    failed_reason_counts[failed_reason] = failed_reason_counts.get(failed_reason, 0) + 1
                    failed_models.append({"routing_key": model.routing_key, "reason": failed_reason})
            elif key == "skipped_unsupported":
                skipped += 1
                if reason:
                    skip_reason_counts[reason] = skip_reason_counts.get(reason, 0) + 1
                    skipped_models.append({"routing_key": model.routing_key, "reason": reason})
            else:
                succeeded += 1
        except ValueError as exc:
            msg = str(exc)
            if mode == "live" and "Run heuristic screening first" in msg:
                key = "skipped_precondition"
                reason = "requires_heuristic_first"
                status_counts[key] = status_counts.get(key, 0) + 1
                skip_reason_counts[reason] = skip_reason_counts.get(reason, 0) + 1
                skipped_models.append({"routing_key": model.routing_key, "reason": reason})
                skipped += 1
                continue
            failed += 1
            errors.append(f"{model.routing_key}: {msg}")

    session.commit()
    return AdminBatchEvaluationResponse(
        mode=mode,
        matched_models=len(rows),
        processed_models=len(selected_rows),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        benchmark_status_counts=status_counts,
        skip_reason_counts=skip_reason_counts,
        skipped_models=skipped_models[:100],
        failed_reason_counts=failed_reason_counts,
        failed_models=failed_models[:100],
        error_messages=errors[:20],
    )


@router.get("/requests")
def list_admin_requests(
    session: Annotated[Session, Depends(get_db_session)],
    date_value: Annotated[str, Query(alias="date")],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminRequestListResponse:
    try:
        target_date = date.fromisoformat(date_value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format, use YYYY-MM-DD")

    rows = RequestRepository(session).list_requests_for_date(target_date=target_date, limit=limit)
    items = []
    for row in rows:
        items.append(
            AdminRequestListItem(
                id=str(row.id),
                prompt=row.prompt,
                selected_model=row.selected_model.routing_key if row.selected_model else None,
                status=_request_status_from_row(
                    fallback_used=row.fallback_used,
                    selected_model_id=row.selected_model_id,
                ),
                created_at=row.created_at.isoformat(),
            )
        )
    return AdminRequestListResponse(date=target_date.isoformat(), limit=limit, items=items)


@router.post("/sync/run")
def run_admin_sync(
    session: Annotated[Session, Depends(get_db_session)],
) -> AdminSyncRunResponse:
    result = OpenRouterSyncService(session).sync_models()
    session.commit()
    return AdminSyncRunResponse(
        models_processed=result.models_processed,
        models_created=result.models_created,
        models_updated=result.models_updated,
    )


@router.get("/metrics")
def get_admin_metrics(
    session: Annotated[Session, Depends(get_db_session)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
) -> AdminMetricsSummaryResponse:
    metrics = MetricsRepository(session).get_summary(days=days)
    total_requests = sum(row.total_requests for row in metrics)
    successful_requests = sum(row.successful_requests for row in metrics)
    failed_requests = sum(row.failed_requests for row in metrics)
    success_rate = round(successful_requests / max(total_requests, 1), 3) if total_requests else 0.0
    avg_latency_ms = (
        round(sum(row.avg_latency_ms * row.total_requests for row in metrics) / total_requests, 2)
        if total_requests
        else 0.0
    )
    unique_sessions_peak = max((row.unique_sessions for row in metrics), default=0)
    return AdminMetricsSummaryResponse(
        days=days,
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        success_rate=success_rate,
        avg_latency_ms=avg_latency_ms,
        unique_sessions_peak=unique_sessions_peak,
    )
