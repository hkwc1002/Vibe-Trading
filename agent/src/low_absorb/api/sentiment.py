"""Sentiment API for Low Absorb — wires global market data into the permission snapshot."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter

from ..a_stock_provider import AStockLowAbsorbProvider
from ..data_provider import GlobalMarketDataProvider, MarketBreadth
from ..sentiment import build_sentiment_permission_snapshot, compute_global_risk_appetite
from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/sentiment", tags=["low-absorb"])

# Injected providers — replaceable in tests via setter functions.
_global_provider: GlobalMarketDataProvider | None = None
_a_stock_provider: AStockLowAbsorbProvider | None = None


def set_global_provider(provider: GlobalMarketDataProvider | None) -> None:
    """Allow tests or runtime wiring to inject a global market provider."""
    global _global_provider
    _global_provider = provider


def set_a_stock_provider(provider: AStockLowAbsorbProvider | None) -> None:
    """Allow tests or runtime wiring to inject an A-share market provider."""
    global _a_stock_provider
    _a_stock_provider = provider


def _get_global_provider() -> GlobalMarketDataProvider:
    """Return the active global provider, creating one with Stooq defaults if needed."""
    if _global_provider is not None:
        return _global_provider
    config = get_workbench_storage().get_config()
    provider_mode = config.global_market_provider if hasattr(config, "global_market_provider") else "auto"
    return GlobalMarketDataProvider(provider=provider_mode if provider_mode != "auto" else "stooq")


def _get_a_stock_provider() -> AStockLowAbsorbProvider:
    """Return the active A-share provider, creating one with defaults if needed."""
    if _a_stock_provider is not None:
        return _a_stock_provider
    return AStockLowAbsorbProvider()


@router.get("")
def get_sentiment() -> dict[str, object]:
    return {"snapshot": get_sentiment_snapshot()}


@router.get("/snapshot")
def get_sentiment_snapshot() -> dict[str, object]:
    config = get_workbench_storage().get_config()
    provider = _get_global_provider()
    global_risk_appetite, global_risk_error = compute_global_risk_appetite(
        provider, trade_date=date.today(),
    )

    # Fetch A-share market breadth (fail-closed: on error pass None)
    a_share_turnover_cny: Decimal | None = None  # type: ignore[used-variable]
    a_share_limit_break_rate: Decimal | None = None  # type: ignore[used-variable]
    a_share_advance_count: int | None = None  # type: ignore[used-variable]
    a_share_decline_count: int | None = None  # type: ignore[used-variable]
    try:
        a_provider = _get_a_stock_provider()
        breadth = a_provider.get_market_breadth(date.today(), datetime.now())
        if breadth is not None:
            a_share_turnover_cny = breadth.total_market_turnover_cny
            a_share_limit_break_rate = breadth.limit_break_rate
            a_share_advance_count = breadth.advance_count
            a_share_decline_count = breadth.decline_count
    except Exception:
        pass  # fail-closed: values stay None

    snapshot = build_sentiment_permission_snapshot(
        config,
        global_risk_appetite=global_risk_appetite,
        global_risk_error=global_risk_error,
        a_share_turnover_cny=a_share_turnover_cny,
        a_share_limit_break_rate=a_share_limit_break_rate,
        a_share_advance_count=a_share_advance_count,
        a_share_decline_count=a_share_decline_count,
    )
    return {
        **snapshot,
        "snapshot": {
            "compositeScore": snapshot["gauges"][1]["score"],
            "macroGate": snapshot["tradingPermission"]["status"],
            "marketTurnoverCny": snapshot["instrumentPanels"][0]["value"],
            "limitBreakRate": snapshot["instrumentPanels"][1]["value"],
            "globalRiskAppetite": snapshot["instrumentPanels"][4]["value"],
            "aiCapitalTemperature": snapshot["instrumentPanels"][3]["value"],
        },
    }
