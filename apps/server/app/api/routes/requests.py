from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlmodel import Session

from app.api.dependencies.orchestrator import get_db_session
from packages.infrastructure.db.models.llm_request import LLMRequest
from packages.infrastructure.db.repositories.feedback_repository import FeedbackRepository
from packages.infrastructure.db.repositories.request_repository import RequestRepository
from packages.schemas.request_history import (
    AttemptDetail,
    ExecutionDetail,
    FeedbackDetail,
    FeedbackRequest,
    ModelEvaluationDetail,
    RequestAnalysisDetail,
    RequestDetailResponse,
    RequestListItem,
    RequestListResponse,
)

router = APIRouter(prefix="/v1", tags=["requests"])

LIST_PROMPT_MAX = 100
_MSG_NOT_FOUND = "Request not found"


def _truncate_list_prompt(text: str) -> str:
    if len(text) <= LIST_PROMPT_MAX:
        return text
    return text[: LIST_PROMPT_MAX - 1] + "…"


def _selected_model_routing_key(req: LLMRequest) -> str | None:
    if req.selected_model_id is None:
        return None
    sm = req.selected_model
    if sm is not None:
        return sm.routing_key
    return None


def _pick_execution(req: LLMRequest):
    executions = list(req.executions or [])
    if not executions:
        return None
    for ex in executions:
        if ex.success:
            return ex
    return min(executions, key=lambda e: e.created_at)


def _pick_feedback(req: LLMRequest):
    entries = list(req.feedback_entries or [])
    if not entries:
        return None
    return max(entries, key=lambda f: f.created_at)


def _to_request_detail(req: LLMRequest) -> RequestDetailResponse:
    analysis = req.analysis
    analysis_detail = None
    if analysis is not None:
        analysis_detail = RequestAnalysisDetail(
            id=analysis.id,
            task_type=analysis.task_type,
            complexity_score=analysis.complexity_score,
            cost_sensitivity=analysis.cost_sensitivity,
            latency_sensitivity=analysis.latency_sensitivity,
            detected_skills=analysis.detected_skills,
            tokens_estimated=analysis.tokens_estimated,
            created_at=analysis.created_at,
        )

    evaluations_sorted = sorted(
        req.evaluations or [],
        key=lambda e: e.evaluation_rank,
    )
    eval_details = [
        ModelEvaluationDetail(
            model_id=ev.model_id,
            quality_score=int(round(ev.quality_score)),
            latency_score=int(round(ev.latency_score)),
            cost_score=int(round(ev.cost_score)),
            final_score=ev.final_score,
            evaluation_rank=ev.evaluation_rank,
            explanation=ev.explanation,
            pros=list(ev.pros) if ev.pros else None,
            cons=list(ev.cons) if ev.cons else None,
        )
        for ev in evaluations_sorted
    ]

    ex = _pick_execution(req)
    execution_detail = None
    if ex is not None:
        model_routing_key = None
        if ex.model is not None:
            model_routing_key = ex.model.routing_key
        execution_detail = ExecutionDetail(
            id=ex.id,
            model_id=ex.model_id,
            model_routing_key=model_routing_key,
            input_tokens=ex.input_tokens,
            output_tokens=ex.output_tokens,
            latency_ms=ex.latency_ms,
            cost=ex.cost,
            success=ex.success,
            error=ex.error,
            created_at=ex.created_at,
        )

    attempts_sorted = sorted(req.attempts or [], key=lambda a: a.attempt_order)
    attempt_details = [
        AttemptDetail(
            provider_slug=a.provider_slug,
            model_routing_key=a.model_routing_key,
            attempt_order=a.attempt_order,
            status=a.status,
            error=a.error,
            latency_ms=a.latency_ms,
        )
        for a in attempts_sorted
    ]

    fb = _pick_feedback(req)
    feedback_detail = None
    if fb is not None:
        feedback_detail = FeedbackDetail(
            id=fb.id,
            request_id=fb.request_id,
            model_id=fb.model_id,
            rating=fb.rating,
            comment=fb.comment,
            created_at=fb.created_at,
        )

    return RequestDetailResponse(
        id=req.id,
        prompt=req.prompt,
        intent=req.intent,
        priority=req.priority,
        require_json=req.require_json,
        fallback_used=req.fallback_used,
        created_at=req.created_at,
        selected_model=_selected_model_routing_key(req),
        analysis=analysis_detail,
        evaluations=eval_details,
        execution=execution_detail,
        attempts=attempt_details,
        feedback=feedback_detail,
    )


@router.get("/requests")
def list_requests(
    session: Annotated[Session, Depends(get_db_session)],
    x_session_id: Annotated[str | None, Header(alias="X-Session-Id")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RequestListResponse:
    if not x_session_id:
        return RequestListResponse(items=[], total=0, limit=limit, offset=offset)

    repo = RequestRepository(session)
    rows = repo.list_requests_by_session(
        session_id=x_session_id, limit=limit, offset=offset
    )
    total = repo.count_requests_by_session(session_id=x_session_id)
    items = [
        RequestListItem(
            id=r.id,
            prompt=_truncate_list_prompt(r.prompt),
            intent=r.intent,
            priority=r.priority,
            selected_model=_selected_model_routing_key(r),
            fallback_used=r.fallback_used,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return RequestListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/requests/{request_id}")
def get_request_detail(
    request_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    x_session_id: Annotated[str, Header(alias="X-Session-Id")],
) -> RequestDetailResponse:
    if not x_session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-Session-Id required")

    repo = RequestRepository(session)
    row = repo.get_request_by_id(request_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_MSG_NOT_FOUND)
    if row.session_id != x_session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session mismatch")

    full = repo.get_request_with_details(request_id=request_id, session_id=x_session_id)
    if full is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_MSG_NOT_FOUND)
    return _to_request_detail(full)


@router.post(
    "/requests/{request_id}/feedback",
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    request_id: UUID,
    payload: FeedbackRequest,
    session: Annotated[Session, Depends(get_db_session)],
    x_session_id: Annotated[str, Header(alias="X-Session-Id")],
) -> FeedbackDetail:
    if not x_session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-Session-Id required")

    repo = RequestRepository(session)
    row = repo.get_request_by_id(request_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_MSG_NOT_FOUND)
    if row.session_id != x_session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session mismatch")
    if row.selected_model_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No model selected for this request; cannot record feedback",
        )

    fb_repo = FeedbackRepository(session)
    saved = fb_repo.save_feedback(
        request_id=request_id,
        model_id=row.selected_model_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return FeedbackDetail(
        id=saved.id,
        request_id=saved.request_id,
        model_id=saved.model_id,
        rating=saved.rating,
        comment=saved.comment,
        created_at=saved.created_at,
    )
