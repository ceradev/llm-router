from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.api.routes.gateway import router as gateway_router
from app.api.routes.health import router as health_router
from app.api.routes.providers import router as providers_router
from app.api.routes.requests import router as requests_router
from app.api.routes.sync import router as sync_router
from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.db.alembic_runner import run_migrations
from packages.infrastructure.db.repositories.model_repository import ModelRepository
from packages.infrastructure.db.session import engine
from packages.infrastructure.db.seeds.seed_models import seed_initial_models
from packages.services.sync.openrouter_sync_service import OpenRouterSyncService

logger = logging.getLogger(__name__)


async def _periodic_openrouter_sync() -> None:
    settings = get_settings()
    interval = max(60.0, float(settings.openrouter_sync_interval_hours) * 3600.0)
    while True:
        await asyncio.sleep(interval)
        try:
            with Session(engine) as session:
                OpenRouterSyncService(session).sync_models()
                session.commit()
            logger.info("Periodic OpenRouter sync finished")
        except Exception:
            logger.exception("Periodic OpenRouter sync failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations()
    settings = get_settings()
    if settings.seed_models_on_startup:
        try:
            with Session(engine) as session:
                if ModelRepository(session).count_llm_models() == 0:
                    seed_initial_models(session)
                    session.commit()
                    logger.info("Initial model seed completed (empty database)")
        except Exception:
            logger.exception("Initial model seed failed")

    if settings.openrouter_sync_on_startup:
        try:
            with Session(engine) as session:
                OpenRouterSyncService(session).sync_models()
                session.commit()
            logger.info("Startup OpenRouter sync finished")
        except Exception:
            logger.exception("Startup OpenRouter sync failed")

    task: asyncio.Task[None] | None = None
    if settings.openrouter_enable_periodic_sync:
        task = asyncio.create_task(_periodic_openrouter_sync())
    yield
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLM Gateway",
        version="0.1.0",
        description="Smart router for selecting models, tuning parameters, and applying fallbacks.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:4321",
            "http://127.0.0.1:4321",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(gateway_router)
    app.include_router(requests_router)
    app.include_router(providers_router)
    app.include_router(sync_router)
    return app


app = create_app()
