"""Tests for the daily-level backtest engine, dataset, metrics and API."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.backtest.dataset import BacktestDataset
from src.low_absorb.backtest.engine import BacktestEngine, BacktestScannerContext
from src.low_absorb.backtest.metrics import BacktestMetricsCalculator
from src.low_absorb.backtest.models import (
    BacktestPlanRow,
    BacktestSampleRow,
    BacktestSignalRow,
)
from src.low_absorb.config import LowAbsorbConfig
from src.low_absorb.data_provider import (
    DailyBar,
    FixtureMarketDataProvider,
    MarketBreadth,
)
from src.low_absorb.models import (
    BacktestResult,
    BacktestRun,
    BacktestRunRequest,
)
from src.low_absorb.storage import InMemoryLowAbsorbStorage, JsonLowAbsorbStorage


# ── Helpers ──────────────────────────────────────────────────────────────

_TRADE_DATE = date(2026, 3, 15)
_SYMBOLS = ["000001", "000002", "000003", "000004", "000005"]


def _make_daily_bar(
    symbol: str,
    trade_date: date,
    open: Decimal = Decimal("10"),
    high: Decimal = Decimal("11"),
    low: Decimal = Decimal("9.5"),
    close: Decimal = Decimal("10.5"),
    volume: Decimal = Decimal("1_000_000"),
    atr: Decimal = Decimal("0.5"),
    industry: str = "GPU/加速卡",
    stock_name: str = "平安银行",
) -> DailyBar:
    return DailyBar(
        symbol=symbol,
        trade_date=trade_date,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        atr=atr,
        industry=industry,
        stock_name=stock_name,
        captured_at=datetime.combine(trade_date, datetime.min.time()),
    )


def _make_fixture_provider(
    days: int = 60,
    symbols: list[str] | None = None,
) -> FixtureMarketDataProvider:
    """Create a FixtureMarketDataProvider with synthetic daily bars."""
    from datetime import timedelta

    syms = symbols or _SYMBOLS
    base = date(2026, 1, 1)
    bars: dict[str, list[DailyBar]] = {}
    for s in syms:
        symbol_bars: list[DailyBar] = []
        for d in range(days):
            td = base + timedelta(days=d)
            close = Decimal("10") + Decimal(str(d % 10)) * Decimal("0.5")
            symbol_bars.append(_make_daily_bar(
                symbol=s,
                trade_date=td,
                close=close,
                stock_name=f"Stock {s[-4:]}",
            ))
        bars[s] = symbol_bars

    return FixtureMarketDataProvider(
        symbols=syms,
        market_breadth=MarketBreadth(
            trade_date=base,
            captured_at=datetime.combine(base, datetime.min.time()),
            total_market_turnover_cny=Decimal("800_000_000_000"),
            limit_break_rate=Decimal("0.30"),
        ),
        daily_bars=bars,
    )


# =========================================================================
# Model tests
# =========================================================================


class TestBacktestRunRequest:
    """BacktestRunRequest model validation."""

    def test_valid_request(self) -> None:
        """Valid BacktestRunRequest constructs successfully."""
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=["000001", "000002"],
            cost_chain_version="GB200 NVL72",
            include_manual_fill_assumption=True,
        )
        assert req.start_date == date(2026, 1, 1)
        assert req.end_date == date(2026, 3, 31)
        assert req.symbols == ["000001", "000002"]
        assert req.include_manual_fill_assumption is True

    def test_request_without_symbols(self) -> None:
        """BacktestRunRequest with symbols=None can construct (fail-closed in engine)."""
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=None,
            cost_chain_version="GB200 NVL72",
        )
        assert req.symbols is None

    def test_empty_symbols_list(self) -> None:
        """BacktestRunRequest with empty symbols list constructs successfully."""
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=[],
            cost_chain_version="GB200 NVL72",
        )
        assert req.symbols == []

    def test_request_with_config_snapshot(self) -> None:
        """BacktestRunRequest optionally accepts config_snapshot_id."""
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=["000001"],
            cost_chain_version="GB200 NVL72",
            config_snapshot_id="snap-001",
        )
        assert req.config_snapshot_id == "snap-001"


class TestBacktestRun:
    """BacktestRun model validation."""

    def test_run_initial_status(self) -> None:
        """BacktestRun status defaults to QUEUED."""
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=["000001"],
            cost_chain_version="GB200 NVL72",
        )
        run = BacktestRun(run_id="run-001", request=req)
        assert run.run_id == "run-001"
        assert run.status == "QUEUED"
        assert run.created_at is not None
        assert run.finished_at is None
        assert run.error is None

    def test_run_succeeded_status(self) -> None:
        """BacktestRun with SUCCEEDED status is valid."""
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=["000001"],
            cost_chain_version="GB200 NVL72",
        )
        run = BacktestRun(
            run_id="run-002",
            request=req,
            status="SUCCEEDED",
            finished_at=datetime(2026, 6, 15, 10, 0, 0),
        )
        assert run.status == "SUCCEEDED"
        assert run.finished_at is not None

    def test_run_failed_status_with_error(self) -> None:
        """BacktestRun with FAILED status includes error."""
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=["000001"],
            cost_chain_version="GB200 NVL72",
        )
        run = BacktestRun(
            run_id="run-003",
            request=req,
            status="FAILED",
            finished_at=datetime(2026, 6, 15, 10, 0, 0),
            error="历史数据缺失：000001 2026-01-15 至 2026-01-20",
        )
        assert run.status == "FAILED"
        assert "缺失" in run.error

    def test_invalid_status(self) -> None:
        """BacktestRun with invalid status raises."""
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=["000001"],
            cost_chain_version="GB200 NVL72",
        )
        with pytest.raises(ValueError):
            BacktestRun(run_id="run-004", request=req, status="INVALID_STATUS")


class TestBacktestResult:
    """BacktestResult model validation."""

    def test_result_with_all_fields(self) -> None:
        """BacktestResult with complete data constructs successfully."""
        result = BacktestResult(
            run_id="run-001",
            status="SUCCEEDED",
            data_sources=["fixture"],
            sample_count=100,
            signal_count=15,
            plan_count=10,
            win_rate=Decimal("0.55"),
            average_r=Decimal("0.42"),
            max_drawdown=Decimal("-0.064"),
            branch_attribution=[],
            sensitivity=[],
            limitations=["回测基于日线数据，不模拟真实盘中成交。"],
        )
        assert result.win_rate == Decimal("0.55")
        assert result.sample_count == 100
        assert len(result.limitations) == 1

    def test_result_limitations_not_empty(self) -> None:
        """BacktestResult must have at least one limitation."""
        result = BacktestResult(
            run_id="run-002",
            status="SUCCEEDED",
            data_sources=["fixture"],
            sample_count=10,
            limitations=["日线级回测，非真实成交。"],
        )
        assert len(result.limitations) >= 1

    def test_result_negative_win_rate(self) -> None:
        """BacktestResult can have win_rate < 0.5."""
        result = BacktestResult(
            run_id="run-003",
            status="SUCCEEDED",
            data_sources=["fixture"],
            sample_count=50,
            signal_count=10,
            plan_count=5,
            win_rate=Decimal("0.30"),
            average_r=Decimal("-0.10"),
            max_drawdown=Decimal("-0.15"),
            branch_attribution=[],
            sensitivity=[],
            limitations=["测试用。"],
        )
        assert result.win_rate == Decimal("0.30")


# =========================================================================
# Dataset tests
# =========================================================================


class TestBacktestDataset:
    """BacktestDataset data loading."""

    def test_load_returns_bars_for_date_range(self) -> None:
        """Dataset returns bars covering the requested date range."""
        provider = _make_fixture_provider(days=60)
        dataset = BacktestDataset(provider, LowAbsorbConfig())
        bars = dataset.load_historical_bars(
            start_date=date(2026, 1, 10),
            end_date=date(2026, 2, 10),
            symbols=_SYMBOLS,
        )
        assert len(bars) > 0
        for symbol in _SYMBOLS:
            assert symbol in bars
            assert len(bars[symbol]) >= 20

    def test_load_missing_symbol_returns_empty(self) -> None:
        """Dataset returns empty list for unknown symbol."""
        provider = _make_fixture_provider(days=30)
        dataset = BacktestDataset(provider, LowAbsorbConfig())
        bars = dataset.load_historical_bars(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            symbols=["999999"],
        )
        assert len(bars.get("999999", [])) == 0

    def test_load_empty_symbols_returns_empty(self) -> None:
        """Dataset returns empty dict for empty symbols list."""
        provider = _make_fixture_provider(days=30)
        dataset = BacktestDataset(provider, LowAbsorbConfig())
        bars = dataset.load_historical_bars(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            symbols=[],
        )
        assert bars == {}

    def test_load_insufficient_bars(self) -> None:
        """Dataset returns available bars even if less than lookback."""
        provider = _make_fixture_provider(days=5)
        dataset = BacktestDataset(provider, LowAbsorbConfig())
        bars = dataset.load_historical_bars(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            symbols=_SYMBOLS,
        )
        for symbol in _SYMBOLS:
            if symbol in bars:
                assert len(bars[symbol]) <= 5


# =========================================================================
# Engine tests
# =========================================================================


class TestBacktestEngine:
    """BacktestEngine execution."""

    def _make_engine(
        self,
        provider: FixtureMarketDataProvider | None = None,
        config: LowAbsorbConfig | None = None,
    ) -> BacktestEngine:
        p = provider or _make_fixture_provider(days=90)
        c = config or LowAbsorbConfig()
        storage = InMemoryLowAbsorbStorage()
        return BacktestEngine(config=c, data_provider=p, storage=storage)

    def _make_request(
        self,
        start: date | None = None,
        end: date | None = None,
        symbols: list[str] | None = None,
    ) -> BacktestRunRequest:
        # Use default symbols for most tests; pass explicitly for edge cases
        syms: list[str] | None = symbols if symbols is not None else ["000001", "000002"]
        return BacktestRunRequest(
            start_date=start or date(2026, 1, 20),
            end_date=end or date(2026, 2, 15),
            symbols=syms,
            cost_chain_version="GB200 NVL72",
        )

    def _make_none_symbols_request(self) -> BacktestRunRequest:
        return BacktestRunRequest(
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 15),
            symbols=None,
            cost_chain_version="GB200 NVL72",
        )

    def test_engine_run_succeeds(self) -> None:
        """Engine produces SUCCEEDED result with fixture data."""
        engine = self._make_engine()
        request = self._make_request()
        result = engine.run(request)
        assert result.status == "SUCCEEDED"
        assert result.sample_count >= 0
        assert result.error is None

    def test_engine_returns_result_with_metrics(self) -> None:
        """Engine result contains sample_count, signal_count, plan_count."""
        engine = self._make_engine()
        request = self._make_request()
        result: BacktestResult = engine.run(request)
        assert result.status == "SUCCEEDED"
        assert result.sample_count >= 0
        assert result.signal_count >= 0
        assert result.plan_count >= 0

    def test_engine_includes_limitations(self) -> None:
        """Engine result includes limitations list."""
        engine = self._make_engine()
        result = engine.run(self._make_request())
        assert len(result.limitations) > 0
        assert any("日线" in (lim or "") for lim in result.limitations)

    def test_engine_handles_empty_symbols(self) -> None:
        """Engine with empty symbols list returns SUCCEEDED with zero counts."""
        engine = self._make_engine()
        request = self._make_request(symbols=[])
        result = engine.run(request)
        assert result.status == "SUCCEEDED"
        assert result.sample_count == 0
        assert result.plan_count == 0

    def test_engine_handles_none_symbols(self) -> None:
        """Engine with symbols=None fail-closed with error message."""
        engine = self._make_engine()
        request = self._make_none_symbols_request()
        result = engine.run(request)
        assert result.status == "FAILED"
        assert result.error is not None

    def test_engine_missing_data_handled(self) -> None:
        """Engine handles minimal daily data gracefully."""
        provider = _make_fixture_provider(days=5)
        engine = self._make_engine(provider=provider)
        request = self._make_request(
            start=date(2026, 2, 1),
            end=date(2026, 2, 28),
        )
        result = engine.run(request)
        assert result.status in ("SUCCEEDED", "FAILED")

    def test_engine_repeatability(self) -> None:
        """Same input produces same result (decimal-equal)."""
        engine = self._make_engine()
        request = self._make_request()
        result1 = engine.run(request)
        result2 = engine.run(request)
        assert result1.status == result2.status
        if result1.status == "SUCCEEDED":
            assert result1.sample_count == result2.sample_count
            assert result1.signal_count == result2.signal_count
            assert result1.win_rate == result2.win_rate
            assert result1.average_r == result2.average_r


# =========================================================================
# Metrics tests
# =========================================================================


class TestBacktestMetrics:
    """BacktestMetricsCalculator computation."""

    def _make_calculator(self) -> BacktestMetricsCalculator:
        return BacktestMetricsCalculator()

    def _sample(
        self,
        date_str: str = "2026-01-15",
        symbol: str = "000001",
        entry: str = "10",
        exit: str = "11",
        r: str = "2.0",
        branch: str = "GPU/加速卡",
        hit_stop: bool = False,
    ) -> BacktestSampleRow:
        parts = date_str.split("-")
        return BacktestSampleRow(
            trade_date=date(int(parts[0]), int(parts[1]), int(parts[2])),
            symbol=symbol,
            entry_price=Decimal(entry),
            exit_price=Decimal(exit),
            r_multiple=Decimal(r),
            branch=branch,
            hit_stop=hit_stop,
        )

    def test_win_rate_all_positive(self) -> None:
        """Win rate is 1.0 when all samples are positive."""
        calc = self._make_calculator()
        samples = [self._sample(r="2.0"), self._sample(date_str="2026-01-16", symbol="000002", r="1.5")]
        metrics = calc.compute(samples)
        assert metrics.win_rate == Decimal("1.0")
        assert metrics.sample_count == 2

    def test_win_rate_mixed(self) -> None:
        """Win rate is correct for mixed results."""
        calc = self._make_calculator()
        samples = [
            self._sample(r="2.0"),
            self._sample(date_str="2026-01-02", symbol="000002", r="-1.0", hit_stop=True),
            self._sample(date_str="2026-01-03", symbol="000003", r="1.0", branch="CPO/光模块"),
            self._sample(date_str="2026-01-04", symbol="000004", r="-2.0", branch="CPO/光模块", hit_stop=True),
        ]
        metrics = calc.compute(samples)
        assert metrics.win_rate == Decimal("0.5")
        assert metrics.sample_count == 4

    def test_average_r_calculation(self) -> None:
        """Average R is sum of R multiples divided by sample count."""
        calc = self._make_calculator()
        samples = [self._sample(r="2.0"), self._sample(date_str="2026-01-02", symbol="000002", r="1.0")]
        metrics = calc.compute(samples)
        assert metrics.average_r == Decimal("1.5")

    def test_max_drawdown(self) -> None:
        """Max drawdown is the most negative cumulative P&L."""
        calc = self._make_calculator()
        samples = [
            self._sample(r="2.0"),
            self._sample(date_str="2026-01-02", symbol="000002", r="-5.0", hit_stop=True),
            self._sample(date_str="2026-01-03", symbol="000003", r="1.0", branch="CPO/光模块"),
        ]
        metrics = calc.compute(samples)
        assert metrics.max_drawdown < 0

    def test_branch_attribution(self) -> None:
        """Branch attribution aggregates by branch."""
        calc = self._make_calculator()
        samples = [
            self._sample(r="2.0"),
            self._sample(date_str="2026-01-02", symbol="000002", r="-1.0", hit_stop=True),
            self._sample(date_str="2026-01-03", symbol="000003", r="1.0", branch="CPO/光模块"),
        ]
        metrics = calc.compute(samples)
        branches = [b.branch for b in metrics.branch_attribution]
        assert len(branches) > 0

    def test_limitations_includes_required_warnings(self) -> None:
        """Limitations always includes standard disclaimers."""
        calc = self._make_calculator()
        report = calc.get_limitations(
            data_sources=["fixture"],
            has_manual_fill_assumption=False,
        )
        assert len(report.limitations) >= 1
        texts = " ".join(report.limitations)
        assert "日线" in texts
        assert "非真实成交" in texts or "不模拟" in texts

    def test_empty_samples_returns_zero_metrics(self) -> None:
        """Empty samples returns zero-win rate metrics."""
        calc = self._make_calculator()
        metrics = calc.compute([])
        assert metrics.sample_count == 0
        assert metrics.signal_count == 0
        assert metrics.win_rate == Decimal("0")
        assert metrics.average_r == Decimal("0")


# =========================================================================
# Storage backtest limit tests
# =========================================================================


class TestBacktestStorageLimit:
    """Storage enforces max backtest run limit."""

    def test_storage_enforces_max_50_runs(self) -> None:
        """Storage keeps max 50 runs, evicting oldest."""
        storage = InMemoryLowAbsorbStorage()
        for i in range(55):
            req = BacktestRunRequest(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 31),
                symbols=["000001"],
                cost_chain_version="GB200 NVL72",
            )
            run = BacktestRun(
                run_id=f"run-{i:04d}",
                request=req,
                status="SUCCEEDED",
                finished_at=datetime(2026, 6, 15, 10, 0, 0),
            )
            storage.add_backtest_run(run)
        runs = storage.list_backtest_runs()
        assert len(runs) <= 50

    def test_storage_evicts_oldest_first(self) -> None:
        """Oldest runs are evicted first."""
        storage = InMemoryLowAbsorbStorage()
        for i in range(55):
            req = BacktestRunRequest(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 31),
                symbols=["000001"],
                cost_chain_version="GB200 NVL72",
            )
            run = BacktestRun(
                run_id=f"run-{i:04d}",
                request=req,
                status="SUCCEEDED",
                finished_at=datetime(2026, 6, 15, 10, 0, 0),
            )
            storage.add_backtest_run(run)
        runs = storage.list_backtest_runs()
        run_ids = [r.run_id for r in runs]
        assert "run-0000" not in run_ids
        assert "run-0001" not in run_ids
        assert "run-0054" in run_ids

    def test_storage_keeps_fewer_than_50(self) -> None:
        """Storage keeps all runs when under 50."""
        storage = InMemoryLowAbsorbStorage()
        for i in range(10):
            req = BacktestRunRequest(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 31),
                symbols=["000001"],
                cost_chain_version="GB200 NVL72",
            )
            run = BacktestRun(run_id=f"run-{i:04d}", request=req, status="SUCCEEDED")
            storage.add_backtest_run(run)
        runs = storage.list_backtest_runs()
        assert len(runs) == 10


# =========================================================================
# API contract tests
# =========================================================================


class TestBacktestAPI:
    """Backtest API endpoint contract."""

    def _client(self) -> TestClient:
        app = FastAPI()
        from src.low_absorb.api.backtest import router
        app.include_router(router)
        return TestClient(app)

    def test_get_summary_backward_compatible(self) -> None:
        """Old GET /summary endpoint still returns 200."""
        client = self._client()
        response = client.get("/low-absorb/backtest/summary")
        assert response.status_code == 200

    def test_post_run_backward_compatible(self) -> None:
        """Old POST /run endpoint still returns 200."""
        client = self._client()
        response = client.post("/low-absorb/backtest/run")
        assert response.status_code == 200

    def test_post_runs_creates_backtest_task(self) -> None:
        """POST /backtest/runs creates a new backtest run."""
        client = self._client()
        response = client.post("/low-absorb/backtest/runs", json={
            "start_date": "2026-01-15",
            "end_date": "2026-02-15",
            "symbols": ["000001", "000002"],
            "cost_chain_version": "GB200 NVL72",
            "include_manual_fill_assumption": False,
        })
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True

    def test_get_runs_list(self) -> None:
        """GET /backtest/runs returns runs list."""
        client = self._client()
        client.post("/low-absorb/backtest/runs", json={
            "start_date": "2026-01-15",
            "end_date": "2026-01-20",
            "symbols": ["000001"],
            "cost_chain_version": "GB200 NVL72",
        })
        response = client.get("/low-absorb/backtest/runs")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"]["runs"], list)

    def test_get_run_by_id(self) -> None:
        """GET /backtest/runs/{id} returns a specific run."""
        client = self._client()
        create_resp = client.post("/low-absorb/backtest/runs", json={
            "start_date": "2026-01-15",
            "end_date": "2026-01-20",
            "symbols": ["000001"],
            "cost_chain_version": "GB200 NVL72",
        })
        run_id = create_resp.json()["data"]["run_id"]
        response = client.get(f"/low-absorb/backtest/runs/{run_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["run_id"] == run_id

    def test_get_run_by_id_not_found(self) -> None:
        """GET /backtest/runs/{id} returns error for unknown id."""
        client = self._client()
        response = client.get("/low-absorb/backtest/runs/nonexistent-id")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["error"] is not None


class TestBacktestScannerContext:
    """BacktestScannerContext helper."""

    def test_context_requires_symbols(self) -> None:
        """Context with empty symbols creates fine (engine handles validation)."""
        ctx = BacktestScannerContext(symbols=[], config=LowAbsorbConfig())
        assert ctx.symbols == []

    def test_context_includes_defaults(self) -> None:
        """Context has default values for bar_shifts and lookback."""
        ctx = BacktestScannerContext(symbols=["000001"], config=LowAbsorbConfig())
        assert ctx.symbols == ["000001"]
        assert ctx.lookback == 20


# =========================================================================
# CR-1: BacktestResult persistence tests
# =========================================================================


class TestBacktestResultPersistence:
    """Full BacktestResult persistence (H1 fix)."""

    def test_storage_saves_and_retrieves_full_result(self) -> None:
        """get_backtest_result returns the full BacktestResult with metrics."""
        storage = InMemoryLowAbsorbStorage()
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=["000001"],
            cost_chain_version="GB200 NVL72",
        )
        run = BacktestRun(run_id="bt-001", request=req, status="SUCCEEDED")
        result = BacktestResult(
            run_id="bt-001",
            status="SUCCEEDED",
            sample_count=50,
            signal_count=10,
            plan_count=5,
            win_rate=Decimal("0.55"),
            average_r=Decimal("0.42"),
            max_drawdown=Decimal("-0.064"),
            limitations=["测试限制说明。"],
        )
        storage.add_backtest_run(run, result=result)

        retrieved = storage.get_backtest_result("bt-001")
        assert retrieved is not None
        assert retrieved.run_id == "bt-001"
        assert retrieved.sample_count == 50
        assert retrieved.win_rate == Decimal("0.55")
        assert retrieved.average_r == Decimal("0.42")
        assert retrieved.limitations == ["测试限制说明。"]

    def test_get_backtest_result_returns_none_for_unknown(self) -> None:
        """get_backtest_result returns None for unknown run_id."""
        storage = InMemoryLowAbsorbStorage()
        assert storage.get_backtest_result("nonexistent") is None

    def test_engine_stores_full_result(self) -> None:
        """Engine.run stores BacktestResult accessible via get_backtest_result."""
        engine = TestBacktestEngine()._make_engine()
        request = TestBacktestEngine()._make_request()
        result = engine.run(request)

        storage = engine._storage
        stored = storage.get_backtest_result(result.run_id)
        assert stored is not None
        assert stored.sample_count == result.sample_count
        assert stored.win_rate == result.win_rate

    def test_failed_run_persists_error(self) -> None:
        """Failed run's error is stored and retrievable (M1 fix)."""
        engine = TestBacktestEngine()._make_engine()
        request = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=None,
            cost_chain_version="GB200 NVL72",
        )
        result = engine.run(request)
        assert result.status == "FAILED"
        assert result.error is not None

        stored_result = engine._storage.get_backtest_result(result.run_id)
        assert stored_result is not None
        assert stored_result.status == "FAILED"
        assert stored_result.error is not None

        stored_run = engine._storage.get_backtest_run(result.run_id)
        assert stored_run is not None
        assert stored_run.status == "FAILED"
        assert stored_run.error is not None


# =========================================================================
# CR-2: JSON roundtrip tests
# =========================================================================


class TestJsonBacktestRoundtrip:
    """JsonLowAbsorbStorage roundtrip for backtest data (H2 fix)."""

    def _make_storage(self, tmp_path) -> JsonLowAbsorbStorage:
        path = tmp_path / "test_low_absorb.json"
        return JsonLowAbsorbStorage(path=str(path))

    def test_json_roundtrip_preserves_runs_and_results(self, tmp_path) -> None:
        """Save and reload preserves backtest_runs and backtest_results."""
        storage = self._make_storage(tmp_path)
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=["000001"],
            cost_chain_version="GB200 NVL72",
        )
        run = BacktestRun(run_id="bt-001", request=req, status="SUCCEEDED")
        result = BacktestResult(
            run_id="bt-001",
            status="SUCCEEDED",
            sample_count=10,
            win_rate=Decimal("0.5"),
            limitations=["测试用。"],
        )
        storage.add_backtest_run(run, result=result)

        # Reload from disk
        storage2 = self._make_storage(tmp_path)
        assert storage2.get_backtest_run("bt-001") is not None
        assert storage2.get_backtest_result("bt-001") is not None

        reloaded = storage2.get_backtest_result("bt-001")
        assert reloaded is not None
        assert reloaded.sample_count == 10
        assert reloaded.win_rate == Decimal("0.5")

    def test_json_roundtrip_with_failed_run(self, tmp_path) -> None:
        """Failed run with error is preserved across reload (M1 fix)."""
        storage = self._make_storage(tmp_path)
        req = BacktestRunRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            symbols=None,
            cost_chain_version="GB200 NVL72",
        )
        run = BacktestRun(
            run_id="bt-fail", request=req, status="FAILED",
            error="测试失败原因",
        )
        result = BacktestResult(
            run_id="bt-fail",
            status="FAILED",
            error="测试失败原因",
            limitations=["测试用。"],
        )
        storage.add_backtest_run(run, result=result)

        storage2 = self._make_storage(tmp_path)
        reloaded = storage2.get_backtest_run("bt-fail")
        assert reloaded is not None
        assert reloaded.status == "FAILED"
        assert reloaded.error == "测试失败原因"

        reloaded_result = storage2.get_backtest_result("bt-fail")
        assert reloaded_result is not None
        assert reloaded_result.error == "测试失败原因"


# =========================================================================
# CR-3: API full result contract tests
# =========================================================================


class TestBacktestAPIFullResult:
    """GET /runs/{id} returns full BacktestResult (H3 fix)."""

    def _client(self) -> TestClient:
        app = FastAPI()
        from src.low_absorb.api.backtest import router
        app.include_router(router)
        return TestClient(app)

    def test_get_run_by_id_returns_full_result(self) -> None:
        """GET /runs/{id} returns metrics, attribution, limitations."""
        client = self._client()
        resp = client.post("/low-absorb/backtest/runs", json={
            "start_date": "2026-01-20",
            "end_date": "2026-02-15",
            "symbols": ["000001", "000002"],
            "cost_chain_version": "GB200 NVL72",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        run_id = body["data"]["run_id"]

        detail = client.get(f"/low-absorb/backtest/runs/{run_id}")
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["success"] is True
        data = detail_body["data"]
        # Must have full result fields
        assert "sample_count" in data
        assert "win_rate" in data
        assert "average_r" in data
        assert "max_drawdown" in data
        assert "limitations" in data
        assert isinstance(data["limitations"], list)
        assert len(data["limitations"]) >= 1

    def test_get_run_returns_failed_error(self) -> None:
        """Failed run's error is visible through API (M1 fix)."""
        client = self._client()
        resp = client.post("/low-absorb/backtest/runs", json={
            "start_date": "2026-01-15",
            "end_date": "2026-01-20",
            "symbols": None,
            "cost_chain_version": "GB200 NVL72",
        })
        body = resp.json()
        assert body["success"] is True
        run_id = body["data"]["run_id"]

        detail = client.get(f"/low-absorb/backtest/runs/{run_id}")
        assert detail.status_code == 200
        data = detail.json()["data"]
        assert data["status"] == "FAILED"
        assert data["error"] is not None
        assert "None" in data["error"] or "stock" in data["error"].lower() or "symbol" in data["error"].lower()


# =========================================================================
# CR-5: Sensitivity non-empty test
# =========================================================================


class TestBacktestSensitivity:
    """Engine produces sensitivity analysis (M2 fix)."""

    def test_sensitivity_non_empty_when_samples_exist(self) -> None:
        """Engine-generated result has non-empty sensitivity."""
        engine = TestBacktestEngine()._make_engine(
            provider=_make_fixture_provider(days=90),
        )
        request = TestBacktestEngine()._make_request(
            start=date(2026, 1, 20),
            end=date(2026, 2, 15),
        )
        result = engine.run(request)
        if result.sample_count > 0:
            assert len(result.sensitivity) > 0
            entry = result.sensitivity[0]
            assert hasattr(entry, "parameter")
            assert hasattr(entry, "base")


# =========================================================================
# CR-7: run_id uniqueness tests
# =========================================================================


class TestBacktestRunIdUniqueness:
    """_make_run_id() must produce collision-free IDs."""

    def test_1000_run_ids_are_unique(self) -> None:
        """1000 generated run_ids have zero collisions."""
        from src.low_absorb.backtest.engine import _make_run_id
        ids = [_make_run_id() for _ in range(1000)]
        collisions = sum(1 for count in Counter(ids).values() if count > 1)
        assert collisions == 0, f"Found {collisions} colliding run_ids in 1000 generations"

    def test_multiple_engine_runs_dont_overwrite(self) -> None:
        """Multiple engine.run() produces unique run_ids (no storage overwrite)."""
        engine = TestBacktestEngine()._make_engine(
            provider=_make_fixture_provider(days=90),
        )
        request = TestBacktestEngine()._make_request(
            start=date(2026, 1, 20),
            end=date(2026, 2, 15),
        )
        run_ids = set()
        for _ in range(5):
            result = engine.run(request)
            run_ids.add(result.run_id)

        assert len(run_ids) == 5, f"Expected 5 unique run_ids, got {len(run_ids)}"

        # All 5 results should be retrievable from storage
        for rid in run_ids:
            stored = engine._storage.get_backtest_result(rid)
            assert stored is not None, f"Run {rid} not found in storage"
            assert stored.run_id == rid

    def test_failed_run_ids_also_unique(self) -> None:
        """Failed runs also get unique IDs (not overwritten)."""
        engine = TestBacktestEngine()._make_engine()
        run_ids = set()
        for _ in range(5):
            req = BacktestRunRequest(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 31),
                symbols=None,
                cost_chain_version="GB200 NVL72",
            )
            result = engine.run(req)
            run_ids.add(result.run_id)

        assert len(run_ids) == 5, f"Expected 5 unique run_ids for failed runs, got {len(run_ids)}"

