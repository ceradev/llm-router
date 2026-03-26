from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_root() -> dict[str, str]:
    return {
        "service": "llm-gateway",
        "message": "Smart router ready",
    }


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
