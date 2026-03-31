from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from packages.infrastructure.db.models.llm_attempt import LLMAttempt


class AttemptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_attempt(
        self,
        *,
        request_id: UUID,
        provider_slug: str,
        model_routing_key: str,
        attempt_order: int,
        status: str,
        error: str | None,
        latency_ms: int | None,
    ) -> LLMAttempt:
        row = LLMAttempt(
            request_id=request_id,
            provider_slug=provider_slug,
            model_routing_key=model_routing_key,
            attempt_order=attempt_order,
            status=status,
            error=error,
            latency_ms=latency_ms,
        )
        self.session.add(row)
        self.session.flush()
        return row
