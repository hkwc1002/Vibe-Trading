"""Tests for A-share orchestrator multi-source fetch (CR-1)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from src.low_absorb.data_sources.a_share_orchestrator import AShareOrchestrator
from src.low_absorb.data_sources.models import DataSourceHealth, MultiSourceFetchResult
from src.low_absorb.data_sources.a_share_adapters import AdapterResult


class TestOrchestratorFetch:
    """CR-1: AShareOrchestrator must perform actual multi-source fetch with fallback."""

    def test_fetch_quote_first_source_success(self) -> None:
        def mock_adapters(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=True, selected_source="mootdx", data={"price": "20.50"}, returned_rows=1))
            return MockAdapter(AdapterResult(ok=False))
        orch = AShareOrchestrator(adapter_factory=mock_adapters)
        result = orch.fetch_quote("601138")
        assert result.ok is True
        assert result.selected_source == "mootdx"
        assert result.fallback_used is False

    def test_fetch_quote_falls_back_on_first_failure(self) -> None:
        def mock_adapters(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=False, error_message="mootdx down"))
            if source_id == "tencent":
                return MockAdapter(AdapterResult(ok=True, selected_source="tencent", data={"price": "20.48"}, returned_rows=1))
            return MockAdapter(AdapterResult(ok=False))
        orch = AShareOrchestrator(adapter_factory=mock_adapters)
        result = orch.fetch_quote("601138")
        assert result.ok is True
        assert result.selected_source == "tencent"
        assert result.fallback_used is True
        assert result.attempts[0].ok is False
        assert result.attempts[1].ok is True

    def test_fetch_all_sources_fail(self) -> None:
        def mock_adapters(source_id: str):
            return MockAdapter(AdapterResult(ok=False, error_message=f"{source_id} unavailable"))
        orch = AShareOrchestrator(adapter_factory=mock_adapters)
        result = orch.fetch_quote("601138")
        assert result.ok is False
        assert result.selected_source is None
        assert result.fail_closed_reason is not None
        assert len(result.attempts) == 4

    def test_fetch_open_source_is_skipped(self) -> None:
        call_log: list[str] = []
        def make_adapter(source_id: str):
            def _fetch(*a, **kw) -> AdapterResult:
                call_log.append(source_id)
                return AdapterResult(ok=True, selected_source=source_id, data={})
            return MockAdapter(_fetch)
        orch = AShareOrchestrator(adapter_factory=make_adapter, failure_threshold=1)
        orch.record_source_failure("mootdx", "err")
        orch.record_source_failure("mootdx", "err")
        assert orch.get_source_health("mootdx").circuit_state == "OPEN"
        orch.fetch_quote("601138")
        assert "mootdx" not in call_log, "OPEN circuit source should be skipped"

    def test_fetch_kline_prefers_mootdx(self) -> None:
        def mock_adapters(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=True, selected_source="mootdx", data=[{"date": "2026-06-14"}], returned_rows=1))
            return MockAdapter(AdapterResult(ok=False))
        orch = AShareOrchestrator(adapter_factory=mock_adapters)
        result = orch.fetch_kline("601138", lookback=5)
        assert result.ok is True
        assert result.selected_source == "mootdx"

    def test_fetch_kline_fallback(self) -> None:
        call_order: list[str] = []
        def make_adapter(source_id: str):
            def _fetch(*a, **kw) -> AdapterResult:
                call_order.append(source_id)
                if source_id in ("mootdx", "tencent"):
                    return AdapterResult(ok=False, error_message=f"{source_id} failed")
                return AdapterResult(ok=True, selected_source=source_id, data=[{"date": "2026-06-14"}], returned_rows=1)
            return MockAdapter(_fetch)
        orch = AShareOrchestrator(adapter_factory=make_adapter)
        result = orch.fetch_kline("601138", lookback=5)
        assert result.ok is True
        assert result.selected_source not in ("mootdx", "tencent")
        assert result.fallback_used is True

    def test_fetch_updates_health_on_success(self) -> None:
        def mock_adapters(source_id: str):
            return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={}, returned_rows=0))
        orch = AShareOrchestrator(adapter_factory=mock_adapters)
        orch.fetch_quote("601138")
        assert orch.get_source_health("mootdx").health_score == Decimal("100")

    def test_fetch_updates_health_on_failure(self) -> None:
        def mock_adapters(source_id: str):
            return MockAdapter(AdapterResult(ok=False, error_message=f"{source_id} fail"))
        orch = AShareOrchestrator(adapter_factory=mock_adapters, failure_threshold=5)
        orch.fetch_quote("601138")
        assert orch.get_source_health("mootdx").health_score < Decimal("100")


class MockAdapter:
    def __init__(self, result: AdapterResult | Callable | None = None) -> None:
        self._result = result or AdapterResult(ok=False)
    def fetch_quote(self, symbol: str) -> AdapterResult:
        return self._result() if callable(self._result) else self._result
    def fetch_kline(self, symbol: str, lookback: int = 20) -> AdapterResult:
        return self._result() if callable(self._result) else self._result


# ── CR-1 Round 2: Conflict detection, staleness, production mode ────────────


class TestOrchestratorQualityGates:
    """Additional quality gates for CR-1."""

    def test_conflict_detected_when_sources_differ(self) -> None:
        """When two sources return different prices > tolerance, ok=False with conflict fail-closed."""
        def make_adapter(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.50"}, returned_rows=1))
            if source_id == "tencent":
                return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "22.00"}, returned_rows=1))
            return MockAdapter(AdapterResult(ok=False))
        orch = AShareOrchestrator(adapter_factory=make_adapter, conflict_tolerance_pct=Decimal("0.02"))
        result = orch.fetch_quote("601138")
        assert result.ok is False
        assert len(result.conflicts) > 0
        assert "conflict" in result.fail_closed_reason.lower()
        assert result.conflicts[0].field in ("close", "price")
        assert result.conflicts[0].severity == "warning"

    def test_no_conflict_when_within_tolerance(self) -> None:
        """When source values are close, no conflicts recorded."""
        def make_adapter(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.50"}, returned_rows=1))
            if source_id == "tencent":
                return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.48"}, returned_rows=1))
            return MockAdapter(AdapterResult(ok=False))
        orch = AShareOrchestrator(adapter_factory=make_adapter, conflict_tolerance_pct=Decimal("0.02"))
        result = orch.fetch_quote("601138")
        assert result.ok is True
        assert len(result.conflicts) == 0

    def test_stale_data_fails_closed(self) -> None:
        """When freshness_seconds > max_staleness, return fail-closed."""
        def make_adapter(source_id: str):
            return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.50"}, returned_rows=1, freshness_seconds=9999))
        orch = AShareOrchestrator(adapter_factory=make_adapter, max_staleness_seconds=60)
        result = orch.fetch_quote("601138")
        assert result.ok is False
        assert result.fail_closed_reason is not None
        assert "stale" in result.fail_closed_reason.lower()

    def test_fresh_data_passes_staleness_check(self) -> None:
        """Fresh data passes staleness check."""
        def make_adapter(source_id: str):
            return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.50"}, returned_rows=1, freshness_seconds=30))
        orch = AShareOrchestrator(adapter_factory=make_adapter, max_staleness_seconds=60)
        result = orch.fetch_quote("601138")
        assert result.ok is True

    def test_production_mode_allows_real_fallback(self) -> None:
        """In production mode, real source fallback (mootdx fails, tencent works) is OK."""
        def make_adapter(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=False, error_message="mootdx down"))
            if source_id == "tencent":
                return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.48"}, returned_rows=1))
            return MockAdapter(AdapterResult(ok=False))
        orch = AShareOrchestrator(adapter_factory=make_adapter, production_mode=True)
        result = orch.fetch_quote("601138")
        assert result.ok is True
        assert result.fallback_used is True
        assert result.selected_source == "tencent"

    def test_production_mode_rejects_fixture_fallback(self) -> None:
        """In production mode, fixture source fallback is rejected."""
        def make_adapter(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=False))
            return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={}, returned_rows=0, is_fixture=True))
        orch = AShareOrchestrator(adapter_factory=make_adapter, production_mode=True)
        result = orch.fetch_quote("601138")
        assert result.ok is False
        assert result.fail_closed_reason is not None
        assert "fixture" in result.fail_closed_reason.lower()

    def test_production_mode_allows_primary_source(self) -> None:
        """In production mode, primary source success is fine."""
        def make_adapter(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.50"}, returned_rows=1))
            return MockAdapter(AdapterResult(ok=False))
        orch = AShareOrchestrator(adapter_factory=make_adapter, production_mode=True)
        result = orch.fetch_quote("601138")
        assert result.ok is True


# ── CR-1 Round 4: check_data_quality reflects actual fetch result ──────────


class TestQualityReflectsFetch:
    """check_data_quality() must carry last fetch's stale/conflict/fail results."""

    def test_quality_false_after_conflict_fetch(self) -> None:
        """After conflict fetch, check_data_quality returns False with conflict reason."""
        def make_adapter(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.50"}, returned_rows=1))
            if source_id == "tencent":
                return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "22.00"}, returned_rows=1))
            return MockAdapter(AdapterResult(ok=False))
        orch = AShareOrchestrator(adapter_factory=make_adapter, conflict_tolerance_pct=Decimal("0.02"))
        orch.fetch_quote("601138")
        ok, reason = orch.check_data_quality()
        assert ok is False
        assert reason is not None
        assert "conflict" in reason.lower()

    def test_quality_false_after_stale_fetch(self) -> None:
        """After stale fetch, check_data_quality returns False with stale reason."""
        def make_adapter(source_id: str):
            return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.50"}, returned_rows=1, freshness_seconds=9999))
        orch = AShareOrchestrator(adapter_factory=make_adapter, max_staleness_seconds=60)
        orch.fetch_quote("601138")
        ok, reason = orch.check_data_quality()
        assert ok is False
        assert reason is not None
        assert "stale" in reason.lower()

    def test_quality_false_after_fixture_fallback(self) -> None:
        """After fixture fallback in production mode, check_data_quality returns False."""
        def make_adapter(source_id: str):
            if source_id == "mootdx":
                return MockAdapter(AdapterResult(ok=False))
            return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={}, returned_rows=0, is_fixture=True))
        orch = AShareOrchestrator(adapter_factory=make_adapter, production_mode=True)
        orch.fetch_quote("601138")
        ok, reason = orch.check_data_quality()
        assert ok is False
        assert reason is not None

    def test_quality_true_after_healthy_fetch(self) -> None:
        """After healthy fetch, check_data_quality returns True."""
        def make_adapter(source_id: str):
            return MockAdapter(AdapterResult(ok=True, selected_source=source_id, data={"close": "20.50"}, returned_rows=1))
        orch = AShareOrchestrator(adapter_factory=make_adapter)
        orch.fetch_quote("601138")
        ok, _ = orch.check_data_quality()
        assert ok is True
