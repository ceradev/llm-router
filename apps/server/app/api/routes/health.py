from __future__ import annotations

import logging

from fastapi import APIRouter
from sqlalchemy import text
from sqlmodel import Session

from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.session import engine

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
def read_root() -> dict[str, str]:
    return {
        "service": "llm-gateway",
        "message": "Smart router ready",
    }


@router.get("/health")
def healthcheck() -> dict[str, str | int | bool]:
    db_connected = False
    models_count = 0
    with Session(engine) as session:
        try:
            session.exec(text("SELECT 1"))
            db_connected = True
            models_count = ModelRepository(session).count_llm_models()
        except Exception:
            logger.exception("Health check database validation failed")

    status = "healthy" if db_connected and models_count > 0 else "degraded"
    return {
        "status": status,
        "db_connected": db_connected,
        "models_in_catalog": models_count,
        "catalog_ready": models_count > 0,
    }
