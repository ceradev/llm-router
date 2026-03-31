from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from packages.infrastructure.db.models.request_analysis import RequestAnalysis


class AnalysisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_analysis(
        self,
        request_id: UUID,
        *,
        task_type: str,
        complexity_score: float,
        cost_sensitivity: float,
        latency_sensitivity: float,
        detected_skills: list[str] | None,
        tokens_estimated: int,
    ) -> RequestAnalysis:
        row = RequestAnalysis(
            request_id=request_id,
            task_type=task_type,
            complexity_score=complexity_score,
            cost_sensitivity=cost_sensitivity,
            latency_sensitivity=latency_sensitivity,
            detected_skills=detected_skills,
            tokens_estimated=tokens_estimated,
        )
        self.session.add(row)
        self.session.flush()
        return row
