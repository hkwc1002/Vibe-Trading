"""Sentiment API for Low Absorb — wires global market data into the permission snapshot."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from ..data_provider import GlobalMarketDataProvider
from ..sentiment import build_sentiment_permission_snapshot, compute_global_risk_appetite
from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/sentiment", tags=["low-absorb"])

# Injected global provider — replaceable in tests via set_global_provider().
_global_provider: GlobalMarketDataProvider | None = None


def set_global_provider(provider: GlobalMarketDataProvider | None) -> None:
    """Allow tests or runtime wiring to inject a global market provider."""
    global _global_provider
    _global_provider = provider


def _get_global_provider() -> GlobalMarketDataProvider:
    """Return the active global provider, creating one with Stooq defaults if needed."""
    if _global_provider is not None:
        return _global_provider
    config = get_workbench_storage().get_config()
    provider_mode = config.global_market_provider if hasattr(config, "global_market_provider") else "auto"
    return GlobalMarketDataProvider(provider=provider_mode if provider_mode != "auto" else "stooq")


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
    snapshot = build_sentiment_permission_snapshot(
        config,
        global_risk_appetite=global_risk_appetite,
        global_risk_error=global_risk_error,
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
