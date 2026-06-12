"""Data provider boundary for Low Absorb strategy inputs."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from .models import ChainBranchSnapshot, SentimentSnapshot


class MarketDataRow(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MarketBreadth(MarketDataRow):
    trade_date: date
    captured_at: datetime
    total_market_turnover_cny: Decimal = Field(..., ge=0)
    limit_break_rate: Decimal = Field(..., ge=0, le=1)


class DailyBar(MarketDataRow):
    symbol: str = Field(..., min_length=1)
    trade_date: date
    open: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    volume: Decimal = Field(..., ge=0)
    atr: Decimal = Field(..., gt=0)
    industry: str = Field(..., min_length=1)
    stock_name: str = Field(..., min_length=1)
    captured_at: datetime | None = None


class IntradayBar(MarketDataRow):
    symbol: str = Field(..., min_length=1)
    trade_date: date
    at: datetime
    open: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    volume: Decimal = Field(..., ge=0)


class ChainBranchStrength(MarketDataRow):
    branch_name: str = Field(..., min_length=1)
    rank: int = Field(..., ge=1)
    total_branches: int = Field(..., ge=1)
    slope: Decimal
    relative_strength: Decimal


class MarketDataProvider(Protocol):
    """Read-only market data boundary used by the scan-tail funnel."""

    def get_market_breadth(self, trade_date: date, at: datetime) -> MarketBreadth | None:
        """Return market breadth and liquidity at scan time."""

    def get_daily_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        """Return daily bars keyed by symbol."""

    def get_intraday_bars(self, symbol: str, trade_date: date, interval: str) -> list[IntradayBar]:
        """Return intraday bars for signal planning."""

    def get_industry_return(self, industry: str, trade_date: date, start: time, end: time) -> Decimal | None:
        """Return industry return for an intraday window."""

    def get_chain_branch_strength(self, trade_date: date, lookback: int) -> list[ChainBranchStrength]:
        """Return AI-chain branch relative strength rows."""


class LowAbsorbDataProvider(MarketDataProvider, Protocol):
    """Backward-compatible provider boundary with legacy snapshot helpers."""

    def get_mainboard_universe(self, trade_date: date) -> list[str]:
        """Return candidate mainboard stock codes for a trade date."""

    def get_sentiment_snapshot(self, trade_date: date) -> SentimentSnapshot | None:
        """Return a macro sentiment snapshot if available."""

    def get_chain_branches(self, trade_date: date) -> list[ChainBranchSnapshot]:
        """Return AI-chain branch snapshots if available."""


class FixtureMarketDataProvider:
    """Deterministic in-memory provider used by Low Absorb tests."""

    def __init__(
        self,
        *,
        symbols: list[str] | None = None,
        market_breadth: MarketBreadth | None = None,
        daily_bars: dict[str, list[DailyBar]] | None = None,
        intraday_bars: dict[str, list[IntradayBar]] | None = None,
        industry_returns: dict[str, Decimal] | None = None,
        chain_strength: list[ChainBranchStrength] | None = None,
    ) -> None:
        self.symbols = symbols or []
        self._market_breadth = market_breadth
        self._daily_bars = daily_bars or {}
        self._intraday_bars = intraday_bars or {}
        self._industry_returns = industry_returns or {}
        self._chain_strength = chain_strength or []

    def get_market_breadth(self, trade_date: date, at: datetime) -> MarketBreadth | None:
        if self._market_breadth and self._market_breadth.trade_date == trade_date:
            return self._market_breadth
        return None

    def get_daily_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        return {
            symbol: [bar for bar in self._daily_bars.get(symbol, []) if bar.trade_date <= end][-lookback:]
            for symbol in symbols
        }

    def get_intraday_bars(self, symbol: str, trade_date: date, interval: str) -> list[IntradayBar]:
        return [bar for bar in self._intraday_bars.get(symbol, []) if bar.trade_date == trade_date]

    def get_industry_return(self, industry: str, trade_date: date, start: time, end: time) -> Decimal | None:
        return self._industry_returns.get(industry)

    def get_chain_branch_strength(self, trade_date: date, lookback: int) -> list[ChainBranchStrength]:
        return list(self._chain_strength)
