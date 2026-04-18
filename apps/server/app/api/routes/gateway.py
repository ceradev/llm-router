from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.dependencies.orchestrator import get_db_session, get_gateway_orchestrator
from packages.domain.gateway import GatewayTask, NoModelsAvailableError, Priority
from packages.schemas.gateway_request import (
    GatewayRequest,
    GatewaySimpleRequest,
    build_default_gateway_task,
)
from packages.schemas.gateway_response import GatewayResponse, ModelSummaryResponse
from packages.schemas.mappers import (
    scored_candidate_to_ranked_response,
    to_attempt_response,
    to_gateway_response,
    to_model_summary_list,
)
from packages.services.execution.fallback_executor import RoutingExhaustedError
from packages.services.orchestration.orchestrator import GatewayOrchestrator
from sqlmodel import Session

router = APIRouter(prefix="/v1", tags=["gateway"])
logger = logging.getLogger(__name__)


def _get_request_orchestrator(session: Session) -> GatewayOrchestrator:
    return get_gateway_orchestrator(session)


def _execute_gateway_completion(
    *,
    orchestrator: GatewayOrchestrator,
    task: GatewayTask,
    response_priority: Priority,
    session_id: str | None = None,
) -> GatewayResponse:
    try:
        result = orchestrator.execute(task, session_id=session_id)
    except NoModelsAvailableError as exc:
        logger.exception("No eligible models available for gateway request")
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc) or "Model catalog not initialized"},
        ) from exc
    except RoutingExhaustedError as exc:
        logger.exception("Routing exhausted for gateway request")
        raise HTTPException(
            status_code=502,
            detail={
                "message": "All candidate models failed",
                "routing_reason": exc.reason,
                "request_id": str(exc.request_id) if exc.request_id else None,
                "ranking": [
                    scored_candidate_to_ranked_response(c).model_dump()
                    for c in exc.scored_candidates
                ],
                "attempts": [
                    to_attempt_response(attempt).model_dump()
                    for attempt in exc.attempts
                ],
            },
        ) from exc

    return to_gateway_response(result, priority=response_priority)


@router.get("/models")
def list_models(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[ModelSummaryResponse]:
    orchestrator = _get_request_orchestrator(session)
    return to_model_summary_list(orchestrator.list_models())


@router.post(
    "/chat/completions/simple",
    responses={
        502: {"description": "All candidate models failed"},
        503: {"description": "No eligible models in database for routing"},
    },
    summary="Complete with default options",
)
def create_completion_simple(
    payload: GatewaySimpleRequest,
    session: Annotated[Session, Depends(get_db_session)],
    x_session_id: Annotated[str | None, Header(alias="X-Session-Id")] = None,
) -> GatewayResponse:
    orchestrator = _get_request_orchestrator(session)
    task = build_default_gateway_task(prompt=payload.prompt)
    return _execute_gateway_completion(
        orchestrator=orchestrator,
        task=task,
        response_priority=task.priority,
        session_id=x_session_id,
    )


@router.post(
    "/chat/completions/advanced",
    responses={
        502: {
            "description": "All candidate models failed",
        },
        503: {
            "description": "No eligible models in database for routing",
        },
    },
    summary="Complete with advanced options",
)
def create_completion_advanced(
    payload: GatewayRequest,
    session: Annotated[Session, Depends(get_db_session)],
    x_session_id: Annotated[str | None, Header(alias="X-Session-Id")] = None,
) -> GatewayResponse:
    orchestrator = _get_request_orchestrator(session)
    task = GatewayTask(
        prompt=payload.prompt,
        priority=payload.priority,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        require_json=payload.require_json,
        simulate_failures=payload.simulate_failures,
        use_cases=payload.use_cases,
        preferred_providers=payload.preferred_providers,
        response_depth=payload.response_depth,
    )
    return _execute_gateway_completion(
        orchestrator=orchestrator,
        task=task,
        response_priority=payload.priority,
        session_id=x_session_id,
    )
