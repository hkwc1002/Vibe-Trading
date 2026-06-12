"""Macro sentiment gate helpers for Low Absorb."""

from __future__ import annotations

from datetime import datetime

from .config import LowAbsorbConfig
from .data_provider import MarketBreadth
from .models import SentimentSnapshot


def macro_gate_passed(snapshot: SentimentSnapshot | None) -> bool:
    """Return whether the macro sentiment gate allows recommendation work."""

    return bool(snapshot and snapshot.gate_passed)


def market_breadth_gate_passed(
    breadth: MarketBreadth | None,
    *,
    config: LowAbsorbConfig,
    at: datetime,
) -> bool:
    """Fail-closed macro gate for the 14:45 scan-tail funnel."""

    if breadth is None:
        return False
    if abs((at - breadth.captured_at).total_seconds()) > config.max_data_staleness_seconds:
        return False
    if breadth.total_market_turnover_cny <= config.min_market_turnover_cny:
        return False
    return breadth.limit_break_rate < config.max_limit_break_rate
