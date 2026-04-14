from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select
from packages.infrastructure.db.models.model_performance_snapshot import ModelPerformanceSnapshot
from packages.infrastructure.db.models.model_health_status import ModelHealthStatus
from packages.infrastructure.db.models.llm_model import LLMModel

def _build_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    LLMModel.__table__.create(engine, checkfirst=True)
    ModelPerformanceSnapshot.__table__.create(engine, checkfirst=True)
    ModelHealthStatus.__table__.create(engine, checkfirst=True)
    return Session(engine)

def test_create_performance_snapshot():
    session = _build_session()
    # Setup: Create a model first
    model = LLMModel(
        display_name="test-model",
        provider_id=1,
        external_model_id="test/test-model",
        routing_key="test-model",
        is_active=True
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    
    # Test creation
    snapshot = ModelPerformanceSnapshot(
        model_id=model.id,
        p50_latency_ms=100.5,
        p95_latency_ms=250.0,
        avg_cost_per_1k_tokens=0.002,
        success_rate_7d=0.99,
        sample_size=1000
    )
    session.add(snapshot)
    session.commit()
    
    # Verify
    statement = select(ModelPerformanceSnapshot).where(ModelPerformanceSnapshot.model_id == model.id)
    results = session.exec(statement).all()
    assert len(results) == 1
    assert results[0].p50_latency_ms == 100.5
    assert results[0].sample_size == 1000
    session.close()

def test_create_health_status():
    session = _build_session()
    # Setup: Create a model first
    model = LLMModel(
        display_name="test-model-health",
        provider_id=1,
        external_model_id="test/test-model-health",
        routing_key="test-model-health",
        is_active=True
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    
    # Test creation
    health = ModelHealthStatus(
        model_id=model.id,
        status="healthy",
        consecutive_failures=0
    )
    session.add(health)
    session.commit()
    
    # Verify
    statement = select(ModelHealthStatus).where(ModelHealthStatus.model_id == model.id)
    result = session.exec(statement).one()
    assert result.status == "healthy"
    assert result.consecutive_failures == 0
    session.close()
