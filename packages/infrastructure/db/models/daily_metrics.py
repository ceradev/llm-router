from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, Float, Integer
from sqlmodel import Field

from packages.infrastructure.db.base import Base

if TYPE_CHECKING:
    pass


class DailyMetrics(Base, table=True):
    __tablename__ = "daily_metrics"

    metric_date: date = Field(
        sa_column=Column(Date, primary_key=True),
    )
    total_requests: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    successful_requests: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    failed_requests: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    avg_latency_ms: float = Field(default=0.0, sa_column=Column(Float, nullable=False))
    unique_sessions: int = Field(default=0, sa_column=Column(Integer, nullable=False))
