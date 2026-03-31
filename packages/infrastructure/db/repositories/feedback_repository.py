from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session
from sqlmodel import select

from packages.infrastructure.db.models.llm_feedback import LLMFeedback


class FeedbackRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_feedback(
        self,
        *,
        request_id: UUID | None,
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

    def get_model_feedback_stats(self, *, model_id: int) -> tuple[float | None, int]:
        stmt = select(func.avg(LLMFeedback.rating), func.count(LLMFeedback.id)).where(
            LLMFeedback.model_id == model_id
        )
        row = self.session.exec(stmt).one()
        avg_rating = float(row[0]) if row[0] is not None else None
        ratings_count = int(row[1])
        return avg_rating, ratings_count

    def get_feedback_stats_by_model_ids(
        self, *, model_ids: list[int]
    ) -> dict[int, tuple[float | None, int]]:
        if not model_ids:
            return {}
        stmt = (
            select(
                LLMFeedback.model_id,
                func.avg(LLMFeedback.rating),
                func.count(LLMFeedback.id),
            )
            .where(LLMFeedback.model_id.in_(model_ids))
            .group_by(LLMFeedback.model_id)
        )
        rows = self.session.exec(stmt).all()
        stats: dict[int, tuple[float | None, int]] = {}
        for model_id, avg_rating, ratings_count in rows:
            stats[int(model_id)] = (
                float(avg_rating) if avg_rating is not None else None,
                int(ratings_count),
            )
        return stats
