from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from packages.infrastructure.db.models.llm_feedback import LLMFeedback


class FeedbackRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_feedback(
        self,
        *,
        request_id: UUID,
        model_id: int,
        rating: int,
        comment: str | None,
    ) -> LLMFeedback:
        row = LLMFeedback(
            request_id=request_id,
            model_id=model_id,
            rating=rating,
            comment=comment,
        )
        self.session.add(row)
        self.session.flush()
        return row
