# apps/server/tests/test_real_time_observer.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from packages.services.real_time_observer.observer import (
    RealTimeObserver,
    _compute_health_multiplier,
    _MIN_HEALTH_MULTIPLIER,
)
from packages.services.real_time_observer.types import RealTimeHealthSnapshot


class TestComputeHealthMultiplier:
    def test_zero_failures_full_health(self):
        m = _compute_health_multiplier(0.0, None)
        assert m == 1.0

    def test_total_failure_clamps_to_minimum(self):
        m = _compute_health_multiplier(1.0, None)
        assert abs(m - _MIN_HEALTH_MULTIPLIER) < 1e-9

    def test_50pct_failure_rate(self):
        m = _compute_health_multiplier(0.5, None)
        # 1.0 - 0.5 * 0.7 = 0.65
        assert abs(m - 0.65) < 1e-9

    def test_latency_spike_applies_penalty(self):
        m_no_spike = _compute_health_multiplier(0.0, 3_000)
        m_spike = _compute_health_multiplier(0.0, 6_000)
        assert m_spike < m_no_spike
        # 1.0 - 0.15 = 0.85
        assert abs(m_spike - 0.85) < 1e-9

    def test_combined_failure_and_latency_spike_clamps(self):
        m = _compute_health_multiplier(1.0, 10_000)
        assert m == _MIN_HEALTH_MULTIPLIER


class TestRealTimeObserver:
    def _mock_session(self, rows):
        session = MagicMock()
        session.exec.return_value.all.return_value = rows
        return session

    def _make_row(self, key, total, failures, avg_latency):
        row = MagicMock()
        row.model_routing_key = key
        row.total = total
        row.failures = failures
        row.avg_latency = avg_latency
        return row

    def test_healthy_model_returns_full_multiplier(self):
        row = self._make_row("openai/gpt-4", 10, 0, 800.0)
        session = self._mock_session([row])
        observer = RealTimeObserver(session, window_minutes=10)
        snapshot = observer.get_health_snapshot()
        signal = snapshot.signals.get("openai/gpt-4")
        assert signal is not None
        assert signal.health_multiplier == 1.0

    def test_degraded_model_returns_reduced_multiplier(self):
        row = self._make_row("openai/gpt-4", 10, 5, 1000.0)
        session = self._mock_session([row])
        observer = RealTimeObserver(session)
        snapshot = observer.get_health_snapshot()
        signal = snapshot.signals["openai/gpt-4"]
        # failure_rate = 0.5 → multiplier = 1 - 0.35 = 0.65
        assert signal.health_multiplier < 1.0
        assert abs(signal.health_multiplier - 0.65) < 1e-6

    def test_single_attempt_ignored_as_noise(self):
        row = self._make_row("openai/gpt-4", 1, 1, None)
        session = self._mock_session([row])
        observer = RealTimeObserver(session)
        snapshot = observer.get_health_snapshot()
        # Only 1 attempt → ignored → no signal entry
        assert "openai/gpt-4" not in snapshot.signals

    def test_unknown_key_returns_default_multiplier(self):
        session = self._mock_session([])
        observer = RealTimeObserver(session)
        snapshot = observer.get_health_snapshot()
        assert snapshot.get_multiplier("unknown/model") == 1.0

    def test_empty_window_returns_empty_snapshot(self):
        session = self._mock_session([])
        observer = RealTimeObserver(session)
        snapshot = observer.get_health_snapshot()
        assert isinstance(snapshot, RealTimeHealthSnapshot)
        assert len(snapshot.signals) == 0
