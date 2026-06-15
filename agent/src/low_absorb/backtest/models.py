"""Internal models for backtest data structures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class BacktestSignalRow:
    """A single signal generated during backtest iteration."""

    trade_date: date
    symbol: str
    branch: str
    priority_score: Decimal


@dataclass(frozen=True)
class BacktestPlanRow:
    """A single trade plan generated during backtest iteration."""

    trade_date: date
    symbol: str
    branch: str
    entry_price: Decimal
    stop_loss: Decimal


@dataclass(frozen=True)
class BacktestSampleRow:
    """A completed backtest sample with outcome measured against forward price."""

    trade_date: date
    symbol: str
    entry_price: Decimal
    exit_price: Decimal
    r_multiple: Decimal
    branch: str
    hit_stop: bool
