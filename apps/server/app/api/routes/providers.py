from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies.orchestrator import get_db_session
from packages.infrastructure.db.repositories.provider_repository import ProviderRepository
from packages.schemas.provider_response import ProviderResponse

router = APIRouter(prefix="/v1", tags=["providers"])


@router.get("/providers", response_model=list[ProviderResponse])
def list_providers(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[ProviderResponse]:
    rows = ProviderRepository(session).list_active()
    return [
        ProviderResponse(
            id=row.id,
            slug=row.slug,
            display_name=row.display_name,
            is_active=row.is_active,
        )
        for row in rows
        if row.id is not None
    ]
