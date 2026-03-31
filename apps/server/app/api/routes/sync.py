from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies.orchestrator import get_db_session
from packages.schemas.sync_models_response import SyncModelsResponse
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService

router = APIRouter(prefix="/v1", tags=["sync"])
logger = logging.getLogger(__name__)


@router.post("/sync/models")
def post_sync_models(
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
