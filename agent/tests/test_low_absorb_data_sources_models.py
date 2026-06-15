"""Tests for the data source quality models."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.low_absorb.data_sources.models import (
    DataConflict,
    DataSourceAttempt,
    DataSourceHealth,
    MultiSourceFetchResult,
)


class TestDataSourceAttempt:
    """DataSourceAttempt: tracks individual source fetch attempts."""

    def test_minimal_attempt(self) -> None:
        attempt = DataSourceAttempt(source_id="mootdx_kline", source_type="mootdx", started_at=datetime(2026, 6, 14, 9, 30))
        assert attempt.source_id == "mootdx_kline"
        assert attempt.source_type == "mootdx"
        assert attempt.ok is False

    def test_successful_attempt(self) -> None:
        now = datetime(2026, 6, 14, 9, 31)
        attempt = DataSourceAttempt(
            source_id="tencent_quote",
            source_type="tencent",
            started_at=now,
            finished_at=now + timedelta(seconds=2),
            ok=True,
            latency_ms=2000,
            returned_rows=50,
        )
        assert attempt.ok is True
        assert attempt.latency_ms == 2000
        assert attempt.returned_rows == 50

    def test_failed_attempt(self) -> None:
        now = datetime(2026, 6, 14, 9, 32)
        attempt = DataSourceAttempt(
            source_id="eastmoney_news",
            source_type="eastmoney",
            started_at=now,
            finished_at=now + timedelta(seconds=1),
            ok=False,
            error_code="HTTP_503",
            error_message="Service unavailable",
        )
        assert attempt.ok is False
        assert attempt.error_code == "HTTP_503"
        assert attempt.error_message == "Service unavailable"

    def test_latency_negative_should_fail(self) -> None:
        with pytest.raises(ValidationError):
            DataSourceAttempt(
                source_id="bad_latency",
                source_type="test",
                started_at=datetime(2026, 6, 14, 9, 30),
                latency_ms=-1,
            )


class TestDataConflict:
    """DataConflict: when multiple sources provide different values."""

    def test_minimal_conflict(self) -> None:
        conflict = DataConflict(
            field="close",
            values_by_source={"tencent": "20.50", "eastmoney": "20.48"},
            severity="warning",
        )
        assert conflict.field == "close"
        assert conflict.values_by_source["tencent"] == "20.50"
        assert conflict.severity == "warning"

    def test_conflict_with_tolerance(self) -> None:
        conflict = DataConflict(
            field="limit_break_rate",
            values_by_source={"mootdx": "0.25", "tencent": "0.32"},
            tolerance=Decimal("0.05"),
            severity="critical",
        )
        assert conflict.tolerance == Decimal("0.05")

    def test_invalid_severity_should_fail(self) -> None:
        with pytest.raises(ValidationError):
            DataConflict(
                field="close",
                values_by_source={"a": "10", "b": "11"},
                severity="unknown",
            )


class TestDataSourceHealth:
    """DataSourceHealth: circuit breaker state and health scoring."""

    def test_initial_health_closed(self) -> None:
        health = DataSourceHealth(source_id="test_source")
        assert health.source_id == "test_source"
        assert health.enabled is True
        assert health.health_score == Decimal("100")
        assert health.circuit_state == "CLOSED"
        assert health.consecutive_failures == 0

    def test_open_circuit(self) -> None:
        now = datetime(2026, 6, 14, 10, 0)
        health = DataSourceHealth(
            source_id="failing_source",
            enabled=True,
            health_score=Decimal("30"),
            circuit_state="OPEN",
            last_failure_at=now,
            cooldown_until=now + timedelta(minutes=5),
            consecutive_failures=5,
        )
        assert health.circuit_state == "OPEN"
        assert health.health_score == Decimal("30")
        assert health.consecutive_failures == 5
        assert health.cooldown_until is not None

    def test_half_open_circuit(self) -> None:
        health = DataSourceHealth(
            source_id="recovering_source",
            health_score=Decimal("50"),
            circuit_state="HALF_OPEN",
            consecutive_failures=3,
        )
        assert health.circuit_state == "HALF_OPEN"
        assert health.enabled is True

    def test_disabled_source(self) -> None:
        health = DataSourceHealth(source_id="disabled_source", enabled=False, circuit_state="OPEN")
        assert health.enabled is False

    def test_health_score_out_of_range_should_fail(self) -> None:
        with pytest.raises(ValidationError):
            DataSourceHealth(source_id="bad_score", health_score=Decimal("-1"))
        with pytest.raises(ValidationError):
            DataSourceHealth(source_id="bad_score_high", health_score=Decimal("101"))

    def test_invalid_circuit_state_should_fail(self) -> None:
        with pytest.raises(ValidationError):
            DataSourceHealth(source_id="bad_state", circuit_state="UNKNOWN")


class TestMultiSourceFetchResult:
    """MultiSourceFetchResult: combined fetch results across sources."""

    def test_success_result(self) -> None:
        now = datetime(2026, 6, 14, 9, 30)
        attempts = [
            DataSourceAttempt(
                source_id="mootdx_kline",
                source_type="mootdx",
                started_at=now,
                finished_at=now + timedelta(seconds=1),
                ok=True,
                latency_ms=1000,
                returned_rows=100,
            ),
        ]
        result = MultiSourceFetchResult(
            ok=True,
            selected_source="mootdx_kline",
            fallback_used=False,
            attempts=attempts,
            data={"key": "value"},
        )
        assert result.ok is True
        assert result.selected_source == "mootdx_kline"
        assert result.fallback_used is False
        assert len(result.attempts) == 1

    def test_fallback_result(self) -> None:
        now = datetime(2026, 6, 14, 9, 30)
        attempts = [
            DataSourceAttempt(
                source_id="mootdx_kline", source_type="mootdx", started_at=now, finished_at=now + timedelta(seconds=1),
                ok=False, error_code="TIMEOUT", error_message="Timeout",
            ),
            DataSourceAttempt(
                source_id="tencent_kline", source_type="tencent", started_at=now + timedelta(seconds=2),
                finished_at=now + timedelta(seconds=3), ok=True, latency_ms=1000, returned_rows=100,
            ),
        ]
        result = MultiSourceFetchResult(
            ok=True,
            selected_source="tencent_kline",
            fallback_used=True,
            attempts=attempts,
            freshness_seconds=30,
        )
        assert result.ok is True
        assert result.selected_source == "tencent_kline"
        assert result.fallback_used is True
        assert result.freshness_seconds == 30

    def test_all_sources_failed(self) -> None:
        now = datetime(2026, 6, 14, 9, 30)
        attempts = [
            DataSourceAttempt(
                source_id="src_a", source_type="a", started_at=now, finished_at=now + timedelta(seconds=1),
                ok=False, error_code="ERR",
            ),
            DataSourceAttempt(
                source_id="src_b", source_type="b", started_at=now + timedelta(seconds=2),
                finished_at=now + timedelta(seconds=3), ok=False, error_code="ERR",
            ),
        ]
        result = MultiSourceFetchResult(
            ok=False,
            selected_source=None,
            fallback_used=False,
            attempts=attempts,
            fail_closed_reason="all data sources unavailable",
        )
        assert result.ok is False
        assert result.selected_source is None
        assert result.fail_closed_reason == "all data sources unavailable"
        assert len(result.attempts) == 2

    def test_with_conflicts(self) -> None:
        conflicts = [
            DataConflict(field="close", values_by_source={"mootdx": "20.50", "eastmoney": "20.48"}, severity="warning"),
        ]
        result = MultiSourceFetchResult(
            ok=True,
            selected_source="mootdx_kline",
            fallback_used=False,
            attempts=[],
            conflicts=conflicts,
            data={"close": "20.50"},
        )
        assert len(result.conflicts) == 1
        assert result.conflicts[0].field == "close"
