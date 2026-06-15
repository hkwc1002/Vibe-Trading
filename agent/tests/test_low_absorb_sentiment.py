"""Tests for the sentiment permission snapshot module."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.low_absorb.sentiment import build_sentiment_permission_snapshot, compute_global_risk_appetite


def test_default_snapshot_uses_fixture_values() -> None:
    """Without real data, global is unavailable so sentiment yields 观察 (fail-closed)."""
    snapshot = build_sentiment_permission_snapshot()
    perm = snapshot["tradingPermission"]
    assert "观察" in str(perm["status"])
    assert any("全球" in r for r in perm["blockedReasons"])


def test_global_risk_appetite_none_forces_observe_or_intercept() -> None:
    """Missing global data must not yield 允许."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=None,
        global_risk_error="Stooq unreachable",
    )
    perm = snapshot["tradingPermission"]
    status = str(perm["status"])
    assert "允许" not in status
    assert "观察" in status or "拦截" in status
    assert any("全球" in r for r in perm["blockedReasons"])


def test_global_risk_appetite_present_yields_global_gauge() -> None:
    """With valid global data, the global gauge shows the score."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("72"),
    )
    gauges = snapshot["gauges"]
    global_gauge = next(g for g in gauges if g["id"] == "global")
    assert global_gauge["score"] == 72
    assert "72" in str(global_gauge["detail"])


def test_global_risk_low_score_reflects_cold_status() -> None:
    """Global score < 40 is labelled 偏冷."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("25"),
    )
    global_gauge = next(g for g in snapshot["gauges"] if g["id"] == "global")
    assert "偏冷" in str(global_gauge["status"])


def test_global_risk_below_30_intercepts() -> None:
    """H4: Global score < 30 → 拦截 regardless of A-share gates."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("20"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.10"),
    )
    perm = snapshot["tradingPermission"]
    assert "拦截" in str(perm["status"])
    assert any("全球风险偏好" in r for r in perm["blockedReasons"])


def test_global_risk_below_50_observes() -> None:
    """H4: Global score 30-49 → 观察 even when A-share gates pass."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("40"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.10"),
    )
    perm = snapshot["tradingPermission"]
    assert "观察" in str(perm["status"])
    assert any("全球风险偏好" in r for r in perm["blockedReasons"])


def test_a_share_turnover_below_threshold_intercepts() -> None:
    """A-share turnover below min_market_turnover_cny yields 拦截."""
    snapshot = build_sentiment_permission_snapshot(
        a_share_turnover_cny=Decimal("100000000000"),
        a_share_limit_break_rate=Decimal("0.10"),
    )
    perm = snapshot["tradingPermission"]
    assert "拦截" in str(perm["status"])
    assert any("成交额" in r or "炸板率" in r for r in perm["blockedReasons"])


def test_a_share_limit_break_above_threshold_intercepts() -> None:
    """A-share limit break rate above max_limit_break_rate yields 拦截."""
    snapshot = build_sentiment_permission_snapshot(
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.50"),
    )
    perm = snapshot["tradingPermission"]
    assert "拦截" in str(perm["status"])


def test_both_gates_pass_and_global_present_yields_allowed() -> None:
    """All inputs healthy and global score >= 50 → 允许."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
    )
    perm = snapshot["tradingPermission"]
    assert "允许" in str(perm["status"])
    assert perm["blockedReasons"] == []


def test_instrument_panels_have_all_six_gates() -> None:
    """Six instrument panels are always present."""
    snapshot = build_sentiment_permission_snapshot()
    panels = snapshot["instrumentPanels"]
    ids = {p["id"] for p in panels}
    expected = {
        "market_turnover",
        "limit_break",
        "advance_decline",
        "ai_capital_temperature",
        "global_risk_appetite",
        "sentiment_conclusion",
    }
    assert ids == expected


def test_each_instrument_panel_has_required_fields() -> None:
    """Every instrument panel has id, label, value, status, explanation."""
    snapshot = build_sentiment_permission_snapshot()
    for panel in snapshot["instrumentPanels"]:
        assert "id" in panel and panel["id"]
        assert "label" in panel and panel["label"]
        assert "value" in panel
        assert "status" in panel and panel["status"]
        assert "explanation" in panel and panel["explanation"]


def test_event_streams_always_return_arrays() -> None:
    """socialEvents and newsEvents are always lists (possibly empty)."""
    snapshot = build_sentiment_permission_snapshot()
    assert isinstance(snapshot.get("socialEvents", None), list)
    assert isinstance(snapshot.get("newsEvents", None), list)


def test_advance_decline_shows_real_data_when_provided() -> None:
    """When advance/decline counts are supplied, the gate shows them."""
    snapshot = build_sentiment_permission_snapshot(
        a_share_advance_count=2800,
        a_share_decline_count=1200,
    )
    panel = next(p for p in snapshot["instrumentPanels"] if p["id"] == "advance_decline")
    assert "2800" in str(panel["value"])
    assert "1200" in str(panel["value"])


def test_advance_decline_shows_dash_when_no_data() -> None:
    """When advance/decline counts are not supplied, the gate shows '—'."""
    snapshot = build_sentiment_permission_snapshot()
    panel = next(p for p in snapshot["instrumentPanels"] if p["id"] == "advance_decline")
    assert panel["value"] == "—"


def test_a_share_data_missing_global_provided_does_not_return_allowed() -> None:
    """H1: A-share data missing + global provided must NOT return 允许."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=None,
        a_share_limit_break_rate=None,
    )
    perm = snapshot["tradingPermission"]
    status = str(perm["status"])
    assert "允许" not in status, f"H1 violated: returned {status}"
    assert any("A 股" in r for r in perm["blockedReasons"]), "block reason should mention A 股"


def test_a_share_data_missing_panels_show_data_missing() -> None:
    """H1: When A-share data is missing, gate panels show 数据缺失."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=None,
        a_share_limit_break_rate=None,
    )
    turnover_panel = next(p for p in snapshot["instrumentPanels"] if p["id"] == "market_turnover")
    assert turnover_panel["status"] == "数据缺失"
    limit_break_panel = next(p for p in snapshot["instrumentPanels"] if p["id"] == "limit_break")
    assert limit_break_panel["status"] == "数据缺失"


def test_a_share_data_normal_with_global_permitted() -> None:
    """H1 regression: A-share + global both OK returns 允许."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
    )
    perm = snapshot["tradingPermission"]
    assert "允许" in str(perm["status"])


# ──────────────────────────────────────────────────────────────────────────────
# H3: compute_global_risk_appetite unit tests
# ──────────────────────────────────────────────────────────────────────────────


class _FakeGlobalProvider:
    """Fake provider returning deterministic daily bars for global risk test."""

    def __init__(self, bars: dict[str, list] | None = None) -> None:
        self._bars = bars or {}

    def get_daily_bars(self, symbols, end, lookback):
        return self._bars


def test_compute_global_risk_returns_score_on_healthy_data() -> None:
    """With valid daily bars, score is computed and error is None."""
    from datetime import date, timedelta
    from src.low_absorb.data_provider import DailyBar

    today = date(2026, 6, 14)
    bars = []
    for i in range(10):
        trade_date = today - timedelta(days=9 - i)
        bars.append(DailyBar(
            symbol="NVDA", trade_date=trade_date,
            open=Decimal("100"), high=Decimal("105"), low=Decimal("98"),
            close=Decimal(str(100 + i * 2)),
            volume=Decimal("1000000"), atr=Decimal("2"),
            industry="US_EQUITY", stock_name="NVDA",
        ))
    provider = _FakeGlobalProvider({"NVDA": bars, "MSFT": bars, "AVGO": bars})

    score, error = compute_global_risk_appetite(provider, trade_date=today)

    assert error is None
    assert score is not None
    assert Decimal("0") <= score <= Decimal("100")


def test_compute_global_risk_returns_error_when_empty() -> None:
    """With no bars at all, error is returned."""
    provider = _FakeGlobalProvider({"NVDA": [], "MSFT": [], "AVGO": []})
    score, error = compute_global_risk_appetite(provider, trade_date=date(2026, 6, 14))
    assert score is None
    assert error is not None


def test_compute_global_risk_returns_error_on_exception() -> None:
    """When provider raises, error is captured."""
    class FailingProvider:
        def get_daily_bars(self, symbols, end, lookback):
            raise ConnectionError("Network down")

    score, error = compute_global_risk_appetite(FailingProvider(), trade_date=date(2026, 6, 14))
    assert score is None
    assert "失败" in str(error) or "Network" in str(error)


# ── CR-2: Data quality-aware sentiment fail-closed ─────────────────────────


def test_a_share_data_unhealthy_intercepts() -> None:
    """CR-2: When a_share_quality_ok=False, must NOT return 允许."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
        a_share_quality_ok=False,
    )
    perm = snapshot["tradingPermission"]
    assert "允许" not in str(perm["status"])


def test_a_share_data_healthy_allows_when_other_gates_pass() -> None:
    """CR-2: When a_share_quality_ok=True and all gates pass, 允许."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
        a_share_quality_ok=True,
    )
    perm = snapshot["tradingPermission"]
    assert "允许" in str(perm["status"])


def test_a_share_data_unhealthy_blocks_regardless_of_values() -> None:
    """CR-2: Even with good economic data, unhealthy data quality blocks."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("75"),
        a_share_turnover_cny=Decimal("1000000000000"),
        a_share_limit_break_rate=Decimal("0.10"),
        a_share_quality_ok=False,
    )
    perm = snapshot["tradingPermission"]
    assert "允许" not in str(perm["status"])
    assert any("数据" in r for r in perm["blockedReasons"])


def test_global_data_unhealthy_intercepts() -> None:
    """CR-2: When global_quality_ok=False, must NOT return 允许."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
        global_quality_ok=False,
    )
    perm = snapshot["tradingPermission"]
    assert "允许" not in str(perm["status"])


def test_default_quality_not_specified_does_not_block() -> None:
    """CR-2: When quality params not specified, existing behavior preserved."""
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
    )
    perm = snapshot["tradingPermission"]
    assert "允许" in str(perm["status"])


# ── CR-3: Sentiment auto-quality via orchestrator ──────────────────────────


def test_sentiment_auto_intercepts_when_orchestrator_unhealthy() -> None:
    """CR-3: When orchestrator has unhealthy A-share sources, sentiment auto-fails."""
    from src.low_absorb.data_sources.a_share_orchestrator import AShareOrchestrator
    orch = AShareOrchestrator(failure_threshold=1)
    orch.record_source_failure("mootdx", "err")
    orch.record_source_failure("mootdx", "err")
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
        orchestrator=orch,
    )
    perm = snapshot["tradingPermission"]
    assert "允许" not in str(perm["status"])


def test_sentiment_auto_allows_when_orchestrator_healthy() -> None:
    """CR-3: When orchestrator is healthy, sentiment proceeds."""
    from src.low_absorb.data_sources.a_share_orchestrator import AShareOrchestrator
    orch = AShareOrchestrator()
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
        orchestrator=orch,
    )
    perm = snapshot["tradingPermission"]
    assert "允许" in str(perm["status"])


# ── CR-3 Round 4: sentiment from real fetch quality ────────────────────────


def test_sentiment_intercepts_when_quality_stale() -> None:
    from src.low_absorb.data_sources.a_share_orchestrator import AShareOrchestrator
    from src.low_absorb.data_sources.a_share_adapters import AdapterResult
    class _S:
        def fetch_quote(self, s: str) -> AdapterResult:
            return AdapterResult(ok=True, selected_source="mootdx", data={"close": "20.50"}, returned_rows=1, freshness_seconds=9999)
        def fetch_kline(self, s: str, l: int = 20) -> AdapterResult:
            return AdapterResult(ok=True, selected_source="mootdx", data=[], returned_rows=0, freshness_seconds=9999)
    orch = AShareOrchestrator(max_staleness_seconds=60)
    orch._adapter_factory = lambda sid: _S()
    orch.fetch_quote("601138")
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
        orchestrator=orch,
    )
    assert "允许" not in str(snapshot["tradingPermission"]["status"])


def test_sentiment_intercepts_when_quality_fail_closed() -> None:
    from src.low_absorb.data_sources.a_share_orchestrator import AShareOrchestrator
    from src.low_absorb.data_sources.a_share_adapters import AdapterResult
    class _F:
        def fetch_quote(self, s: str) -> AdapterResult:
            return AdapterResult(ok=False, error_message="all sources failed")
        def fetch_kline(self, s: str, l: int = 20) -> AdapterResult:
            return AdapterResult(ok=False, error_message="all sources failed")
    orch = AShareOrchestrator(failure_threshold=1)
    orch._adapter_factory = lambda sid: _F()
    orch.record_source_failure("mootdx", "err")
    orch.record_source_failure("mootdx", "err")
    orch.fetch_quote("601138")
    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        a_share_turnover_cny=Decimal("800000000000"),
        a_share_limit_break_rate=Decimal("0.15"),
        orchestrator=orch,
    )
    assert "允许" not in str(snapshot["tradingPermission"]["status"])
