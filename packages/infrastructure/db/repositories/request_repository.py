from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import attributes, selectinload
from sqlmodel import Session, select

from packages.infrastructure.db.models.llm_execution import LLMExecution
from packages.infrastructure.db.models.llm_feedback import LLMFeedback
from packages.infrastructure.db.models.llm_request import LLMRequest
from packages.infrastructure.db.models.model_evaluation import ModelEvaluation
from packages.infrastructure.db.models.request_analysis import RequestAnalysis


class RequestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_request(
        self,
        *,
        prompt: str,
        intent: str,
        priority: str,
        require_json: bool,
        session_id: str | None = None,
    ) -> LLMRequest:
        row = LLMRequest(
            prompt=prompt,
            intent=intent,
            priority=priority,
            require_json=require_json,
            session_id=session_id,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get_request_by_id(self, request_id: UUID) -> LLMRequest | None:
        return self.session.get(LLMRequest, request_id)

    def update_request_outcome(
        self,
        request_id: UUID,
        *,
        selected_model_id: int | None,
        fallback_used: bool,
    ) -> None:
        row = self.session.get(LLMRequest, request_id)
        if row is None:
            return
        row.selected_model_id = selected_model_id
        row.fallback_used = fallback_used
        self.session.add(row)

    def list_requests_by_session(
        self,
        *,
        session_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[LLMRequest]:
        stmt = (
            select(LLMRequest)
            .where(LLMRequest.session_id == session_id)
            .options(selectinload(LLMRequest.selected_model))
            .order_by(LLMRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    def count_requests_by_session(self, *, session_id: str) -> int:
        stmt = select(func.count(LLMRequest.id)).where(LLMRequest.session_id == session_id)
        return int(self.session.exec(stmt).one())

    def get_request_with_details(
        self,
        *,
        request_id: UUID,
        session_id: str | None = None,
    ) -> LLMRequest | None:
        stmt = (
            select(LLMRequest)
            .where(LLMRequest.id == request_id)
            .options(
                selectinload(LLMRequest.selected_model),
                selectinload(LLMRequest.executions).selectinload(LLMExecution.model),
                selectinload(LLMRequest.attempts),
            )
        )
        if session_id is not None:
            stmt = stmt.where(LLMRequest.session_id == session_id)
        row = self.session.exec(stmt).first()
        if row is None:
            return None

        # Load analysis / evaluations separately so SQLite tests without ARRAY tables still work.
        try:
            analysis = self.session.exec(
                select(RequestAnalysis).where(RequestAnalysis.request_id == request_id)
            ).first()
        except OperationalError:
            attributes.set_committed_value(row, "analysis", None)
        else:
            attributes.set_committed_value(row, "analysis", analysis)

        try:
            evals = list(
                self.session.exec(
                    select(ModelEvaluation)
                    .where(ModelEvaluation.request_id == request_id)
                    .options(selectinload(ModelEvaluation.model))
                ).all()
            )
        except OperationalError:
            attributes.set_committed_value(row, "evaluations", [])
        else:
            attributes.set_committed_value(row, "evaluations", evals)

        try:
            feedbacks = list(
                self.session.exec(
                    select(LLMFeedback).where(LLMFeedback.request_id == request_id)
                ).all()
            )
        except OperationalError:
            attributes.set_committed_value(row, "feedback_entries", [])
        else:
            attributes.set_committed_value(row, "feedback_entries", feedbacks)

        return row
