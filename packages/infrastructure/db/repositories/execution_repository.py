from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from packages.infrastructure.db.models.llm_execution import LLMExecution


class ExecutionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_execution(
        self,
        *,
        request_id: UUID,
        model_id: int,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost: float,
        success: bool,
        error: str | None,
    ) -> LLMExecution:
        row = LLMExecution(
            request_id=request_id,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost=cost,
            success=success,
            error=error,
        )
        self.session.add(row)
        self.session.flush()
        return row
