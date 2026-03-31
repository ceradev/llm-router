from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from packages.infrastructure.db.models.model_evaluation import ModelEvaluation


class EvaluationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def bulk_insert_evaluations(self, evaluations: list[ModelEvaluation]) -> None:
        self.session.add_all(evaluations)
        self.session.flush()

    def get_ranked_models(self, request_id: UUID) -> list[ModelEvaluation]:
        stmt = (
            select(ModelEvaluation)
            .where(ModelEvaluation.request_id == request_id)
            .order_by(ModelEvaluation.evaluation_rank)
        )
        return list(self.session.exec(stmt).all())
