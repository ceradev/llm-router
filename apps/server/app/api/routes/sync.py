from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies.orchestrator import get_db_session
from packages.schemas.sync_models_response import SyncModelsResponse
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService

router = APIRouter(prefix="/v1", tags=["sync"])


@router.post("/sync/models", response_model=SyncModelsResponse)
def post_sync_models(
    session: Annotated[Session, Depends(get_db_session)],
) -> SyncModelsResponse:
    service = OpenRouterSyncService(session)
    result = service.sync_models()
    return SyncModelsResponse(
        models_processed=result.models_processed,
        models_created=result.models_created,
        models_updated=result.models_updated,
    )
