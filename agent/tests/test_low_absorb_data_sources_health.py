"""Tests for circuit breaker and health check modules."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from src.low_absorb.data_sources.health import CircuitBreaker, HealthTracker


class TestCircuitBreaker:
    """CircuitBreaker: tracks per-source health with circuit states."""

    def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker(source_id="test_source")
        assert cb.source_id == "test_source"
        assert cb.state == "CLOSED"
        assert cb.health_score == Decimal("100")
        assert cb.consecutive_failures == 0
        assert cb.can_request() is True

    def test_single_success_no_change(self) -> None:
        cb = CircuitBreaker(source_id="test_source")
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.health_score == Decimal("100")

    def test_multiple_successes_cap_at_100(self) -> None:
        cb = CircuitBreaker(source_id="test_source")
        for _ in range(5):
            cb.record_success()
        assert cb.health_score == Decimal("100")

    def test_failure_reduces_score(self) -> None:
        cb = CircuitBreaker(source_id="test_source")
        cb.record_failure("TIMEOUT")
        assert cb.health_score == Decimal("80")
        assert cb.consecutive_failures == 1
        assert cb.state == "CLOSED"

    def test_multiple_failures_open_circuit(self) -> None:
        cb = CircuitBreaker(source_id="test_source", failure_threshold=3)
        for i in range(3):
            cb.record_failure(f"error_{i}")
        assert cb.state == "OPEN"
        assert cb.consecutive_failures == 3
        assert cb.can_request() is False

    def test_open_circuit_stays_open_during_cooldown(self) -> None:
        cb = CircuitBreaker(source_id="test_source", failure_threshold=2, cooldown_seconds=300)
        cb.record_failure("err1")
        cb.record_failure("err2")
        assert cb.state == "OPEN"
        assert cb.can_request() is False

    def test_open_to_half_open_after_cooldown(self) -> None:
        cb = CircuitBreaker(source_id="test_source", failure_threshold=2, cooldown_seconds=0)
        cb.record_failure("err1")
        cb.record_failure("err2")
        assert cb.state == "OPEN"
        assert cb.can_request() is True
        assert cb.state == "HALF_OPEN"

    def test_half_open_success_returns_to_closed(self) -> None:
        cb = CircuitBreaker(source_id="test_source", failure_threshold=2, cooldown_seconds=0)
        cb.record_failure("err1")
        cb.record_failure("err2")
        cb.can_request()
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.consecutive_failures == 0

    def test_half_open_failure_reopens(self) -> None:
        cb = CircuitBreaker(source_id="test_source", failure_threshold=2, cooldown_seconds=0)
        cb.record_failure("err1")
        cb.record_failure("err2")
        cb.can_request()
        cb.record_failure("half_open_fail")
        assert cb.state == "OPEN"
        assert cb.consecutive_failures >= 3

    def test_failure_after_mixed_history(self) -> None:
        cb = CircuitBreaker(source_id="test_source", failure_threshold=3)
        cb.record_success()
        cb.record_failure("err")
        cb.record_success()
        cb.record_failure("err")
        cb.record_success()
        assert cb.consecutive_failures == 0
        assert cb.health_score > Decimal("60")

    def test_health_score_recovery_on_success(self) -> None:
        cb = CircuitBreaker(source_id="test_source", failure_threshold=5)
        cb.record_failure("err")
        assert cb.health_score == Decimal("80")
        cb.record_success()
        assert cb.health_score > Decimal("80")
        for _ in range(10):
            cb.record_success()
        assert cb.health_score <= Decimal("100")

    def test_low_health_after_many_failures(self) -> None:
        cb = CircuitBreaker(source_id="test_source", failure_threshold=10)
        for i in range(8):
            cb.record_failure(f"err{i}")
        assert cb.health_score < Decimal("30")
        # With threshold 10 and only 8 failures, should still be CLOSED
        assert cb.state == "CLOSED"

    def test_status_dict(self) -> None:
        cb = CircuitBreaker(source_id="test_source")
        cb.record_failure("timeout")
        status = cb.status()
        assert status["source_id"] == "test_source"
        assert status["circuit_state"] == "CLOSED"
        assert status["health_score"] == 80.0
        assert status["consecutive_failures"] == 1
        assert status["last_failure_at"] is not None
        assert "cooldown_until" in status


class TestHealthTracker:
    """HealthTracker: manages multiple circuit breakers."""

    def test_get_or_create_breaker(self) -> None:
        tracker = HealthTracker()
        cb = tracker.get_or_create("test_source")
        assert isinstance(cb, CircuitBreaker)
        assert cb.source_id == "test_source"

    def test_get_or_create_returns_same_instance(self) -> None:
        tracker = HealthTracker()
        cb1 = tracker.get_or_create("src_a")
        cb2 = tracker.get_or_create("src_a")
        assert cb1 is cb2

    def test_record_and_retrieve(self) -> None:
        tracker = HealthTracker()
        state = tracker.record_failure("src_a", "timeout")
        assert state["circuit_state"] == "CLOSED"
        assert state["consecutive_failures"] == 1
        tracker.record_success("src_a")
        updated = tracker.record_success("src_a")
        assert updated["consecutive_failures"] == 0

    def test_all_statuses(self) -> None:
        tracker = HealthTracker()
        tracker.record_failure("src_a", "err")
        tracker.get_or_create("src_b")
        statuses = tracker.all_statuses()
        assert "src_a" in statuses
        assert "src_b" in statuses

    def test_unknown_source_success_returns_none(self) -> None:
        tracker = HealthTracker()
        result = tracker.record_success("unknown_source")
        assert result is None

    def test_bulk_status_summary(self) -> None:
        tracker = HealthTracker()
        tracker.record_failure("src_a", "err")
        tracker.record_failure("src_a", "err")
        tracker.get_or_create("src_b")
        tracker.get_or_create("src_c")
        summary = tracker.summary()
        assert "healthy_count" in summary
        assert "degraded_count" in summary
        assert "unhealthy_count" in summary
        assert summary["total_sources"] == 3
