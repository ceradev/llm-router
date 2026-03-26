from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from app.api.presenters.gateway import (
    to_attempt_response,
    to_gateway_response,
    to_model_summary_list,
)
from app.api.schemas.requests import GatewayRequest
from app.api.schemas.responses import GatewayResponse, ModelSummaryResponse
from app.catalog.registry import ModelRegistry
from app.gateway.classify import PromptClassifier
from app.gateway.fallback import FallbackExecutor, RoutingExhaustedError
from app.gateway.orchestrator import GatewayOrchestrator
from app.gateway.select import ModelSelector
from app.gateway.types import GatewayTask
from app.providers.registry import build_provider_clients

router = APIRouter(prefix="/v1", tags=["gateway"])


@lru_cache
def get_gateway_service() -> GatewayOrchestrator:
    registry = ModelRegistry()
    return GatewayOrchestrator(
        registry=registry,
        classifier=PromptClassifier(),
        selector=ModelSelector(registry),
        executor=FallbackExecutor(build_provider_clients()),
    )


@router.get("/models", response_model=list[ModelSummaryResponse])
def list_models(service: GatewayOrchestrator = Depends(get_gateway_service)) -> list[ModelSummaryResponse]:
    return to_model_summary_list(service.list_models())


@router.post("/chat/completions", response_model=GatewayResponse)
def create_completion(
    payload: GatewayRequest,
    service: GatewayOrchestrator = Depends(get_gateway_service),
) -> GatewayResponse:
    try:
        result = service.execute(
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
