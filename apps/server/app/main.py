from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.gateway import router as gateway_router
from app.api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLM Gateway",
        version="0.1.0",
        description="Smart router for selecting models, tuning parameters, and applying fallbacks.",
    )
    app.include_router(health_router)
    app.include_router(gateway_router)
    return app


app = create_app()
