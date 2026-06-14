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
