from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.gateway import get_db_session, get_gateway_orchestrator
from packages.schemas.gateway_request import GatewayRequest
from packages.schemas.gateway_response import GatewayResponse, ModelSummaryResponse
from packages.schemas.mappers import to_attempt_response, to_gateway_response, to_model_summary_list
from packages.services.execution.fallback_executor import RoutingExhaustedError
from packages.domain.gateway import GatewayTask
from sqlmodel import Session

router = APIRouter(prefix="/v1", tags=["gateway"])

@router.get("/models")
def list_models(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[ModelSummaryResponse]:
    orchestrator = get_gateway_orchestrator(session)
    return to_model_summary_list(orchestrator.list_models())


@router.post(
    "/chat/completions",
    responses={
        502: {
            "description": "All candidate models failed",
        }
    },
)
def create_completion(
    payload: GatewayRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> GatewayResponse:
    orchestrator = get_gateway_orchestrator(session)
    try:
        result = orchestrator.execute(
            GatewayTask(
                prompt=payload.prompt,
                priority=payload.priority,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
                require_json=payload.require_json,
                simulate_failures=payload.simulate_failures,
            )
        )
    except RoutingExhaustedError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "All candidate models failed",
                "routing_reason": exc.reason,
                "attempts": [
                    to_attempt_response(attempt).model_dump()
                    for attempt in exc.attempts
                ],
            },
        ) from exc

    return to_gateway_response(result, priority=payload.priority)
