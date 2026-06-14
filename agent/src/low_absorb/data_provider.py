"""Data provider boundary for Low Absorb strategy inputs."""

from __future__ import annotations

import csv
import io
import time as time_module
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Callable, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field
import requests

from .models import ChainBranchSnapshot, SentimentSnapshot


class MarketDataRow(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataFreshnessInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_source: str
    captured_at: datetime | None = None
    market_date: date | None = None
    staleness_seconds: int | None = None
    is_stale: bool = False
    error: str | None = None


class StockNews(MarketDataRow):
    news_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    summary: str = ""
    source: str = ""
    published_at: datetime | None = None
    captured_at: datetime | None = None
    sentiment: Literal["positive", "neutral", "negative"] = "neutral"
    url: str = ""


class StockF10(MarketDataRow):
    symbol: str = Field(..., min_length=1)
    total_shares: Decimal | None = None
    circulating_shares: Decimal | None = None
    pe_ttm: Decimal | None = None
    pb_ratio: Decimal | None = None
    roe_ttm: Decimal | None = None
    industry: str = ""
    main_business: str = ""
    captured_at: datetime | None = None


class MarketBreadth(MarketDataRow):
    trade_date: date
    captured_at: datetime
    total_market_turnover_cny: Decimal = Field(..., ge=0)
    limit_break_rate: Decimal = Field(..., ge=0, le=1)
    advance_count: int | None = None
    decline_count: int | None = None


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

    def get_stock_news(self, symbol: str, trade_date: date) -> list[StockNews]:
        """Return recent news for a stock symbol."""

    def get_freshness_info(self) -> dict[str, DataFreshnessInfo]:
        """Return data source freshness for all data feeds."""


class LowAbsorbDataProvider(MarketDataProvider, Protocol):
    """Backward-compatible provider boundary with legacy snapshot helpers."""

    def get_mainboard_universe(self, trade_date: date) -> list[str]:
        """Return candidate mainboard stock codes for a trade date."""

    def get_sentiment_snapshot(self, trade_date: date) -> SentimentSnapshot | None:
        """Return a macro sentiment snapshot if available."""

    def get_chain_branches(self, trade_date: date) -> list[ChainBranchSnapshot]:
        """Return AI-chain branch snapshots if available."""

    def get_stock_f10(self, symbol: str) -> StockF10 | None:
        """Return F10 fundamentals for an A-share stock."""


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

    def get_stock_news(self, symbol: str, trade_date: date) -> list[StockNews]:
        return []

    def get_freshness_info(self) -> dict[str, DataFreshnessInfo]:
        return {}


def _decimal(value: object, default: str = "0") -> Decimal:
    try:
        if value in (None, ""):
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _stock_secid(symbol: str) -> str:
    code = symbol[-6:]
    market = "1" if code.startswith(("6", "9")) else "0"
    return f"{market}.{code}"


def _ticker_prefix(symbol: str) -> str:
    code = symbol[-6:]
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith(("8", "4")):
        return f"bj{code}"
    return f"sz{code}"


class RateLimitedHttpClient:
    """Small Python HTTP client with Eastmoney-friendly serial throttling."""

    def __init__(
        self,
        *,
        min_interval_seconds: float = 1.0,
        timeout_seconds: float = 8.0,
        session: requests.Session | None = None,
    ) -> None:
        self.min_interval_seconds = min_interval_seconds
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/",
            }
        )
        self._last_call = 0.0

    def get_json(self, url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        wait = self.min_interval_seconds - (time_module.time() - self._last_call)
        if wait > 0:
            time_module.sleep(wait)
        try:
            response = self.session.get(url, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {}
        finally:
            self._last_call = time_module.time()


class ProviderStatusMixin:
    provider_status: dict[str, dict[str, object]]

    def _mark_status(
        self,
        key: str,
        *,
        ok: bool,
        data_source: str,
        message: str = "",
        staleness_seconds: int | None = None,
        captured_at: datetime | None = None,
        market_date: date | None = None,
    ) -> None:
        self.provider_status[key] = {
            "ok": ok,
            "data_source": data_source,
            "message": message,
            "staleness_seconds": staleness_seconds,
            "captured_at": captured_at,
            "market_date": market_date,
        }


# Lazy re-exports for backward compatibility
def __getattr__(name: str):
    if name == "AStockLowAbsorbProvider":
        from .a_stock_provider import AStockLowAbsorbProvider as m
        return m
    if name == "FallbackMarketDataProvider":
        from .fallback_provider import FallbackMarketDataProvider as m
        return m
    if name == "GlobalMarketDataProvider":
        from .global_market_provider import GlobalMarketDataProvider as m
        return m
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
