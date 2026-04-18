from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel import Session

from app.api.dependencies.orchestrator import get_db_session
from packages.infrastructure.config.settings import get_settings
from packages.schemas.sync_models_response import SyncModelsResponse
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService

router = APIRouter(prefix="/v1", tags=["sync"])
logger = logging.getLogger(__name__)


def get_sync_api_key() -> str | None:
    return get_settings().sync_api_key


def require_sync_key(
    x_sync_key: Annotated[str | None, Header(alias="X-Sync-Key")] = None,
    sync_api_key: Annotated[str | None, Depends(get_sync_api_key)] = None,
) -> None:
    if not sync_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sync API key is not configured",
        )
    if not x_sync_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Sync-Key required",
        )
    if x_sync_key != sync_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid sync key",
        )


@router.post("/sync/models")
def post_sync_models(
    _authorized: Annotated[None, Depends(require_sync_key)],
    session: Annotated[Session, Depends(get_db_session)],
) -> SyncModelsResponse:
    logger.info("Manual model sync started")
    service = OpenRouterSyncService(session)
    result = service.sync_models()
    logger.info(
        "Manual model sync finished processed=%s created=%s updated=%s",
        result.models_processed,
        result.models_created,
        result.models_updated,
    )
    return SyncModelsResponse(
        models_processed=result.models_processed,
        models_created=result.models_created,
        models_updated=result.models_updated,
    )
