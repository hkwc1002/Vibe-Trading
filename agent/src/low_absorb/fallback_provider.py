"""Fallback provider combining primary and fixture data sources."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from .data_provider import (
    ChainBranchStrength,
    DailyBar,
    DataFreshnessInfo,
    IntradayBar,
    MarketBreadth,
    MarketDataProvider,
    ProviderStatusMixin,
    StockF10,
    StockNews,
)
class FallbackMarketDataProvider(ProviderStatusMixin):
    """Use a Python provider first and fixture data only when the provider is empty."""

    def __init__(self, *, primary: MarketDataProvider, fallback: MarketDataProvider, enable_fallback: bool = True) -> None:
        self.primary = primary
        self.fallback = fallback
        self._enable_fallback = enable_fallback
        self.symbols = list(getattr(primary, "symbols", []) or getattr(fallback, "symbols", []))
        self.provider_status: dict[str, dict[str, object]] = {}

    def _should_fallback(self) -> bool:
        return self._enable_fallback

    def _maybe_fallback_breadth(self, trade_date: date, at: datetime) -> MarketBreadth | None:
        if not self._should_fallback():
            return None
        fallback = self.fallback.get_market_breadth(trade_date, at)
        self._mark_status("market_breadth", ok=fallback is not None, data_source="fixture_fallback")
        return fallback

    def _maybe_fallback_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        if not self._should_fallback():
            return {symbol: [] for symbol in symbols}
        fallback = self.fallback.get_daily_bars(symbols, end, lookback)
        self._mark_status("daily_bars", ok=any(fallback.values()), data_source="fixture_fallback")
        return fallback

    def _maybe_fallback_intraday(self, symbol: str, trade_date: date, interval: str) -> list[IntradayBar]:
        if not self._should_fallback():
            return []
        fallback = self.fallback.get_intraday_bars(symbol, trade_date, interval)
        self._mark_status("intraday_bars", ok=bool(fallback), data_source="fixture_fallback")
        return fallback

    def _maybe_fallback_industry(self, industry: str, trade_date: date, start: time, end: time) -> Decimal | None:
        if not self._should_fallback():
            return None
        fallback = self.fallback.get_industry_return(industry, trade_date, start, end)
        self._mark_status("industry_return", ok=fallback is not None, data_source="fixture_fallback")
        return fallback

    def _maybe_fallback_chain_strength(self, trade_date: date, lookback: int) -> list[ChainBranchStrength]:
        if not self._should_fallback():
            return []
        fallback = self.fallback.get_chain_branch_strength(trade_date, lookback)
        self._mark_status("chain_strength", ok=bool(fallback), data_source="fixture_fallback")
        return fallback

    def _maybe_fallback_news(self, symbol: str, trade_date: date) -> list[StockNews]:
        if not self._should_fallback():
            return []
        fallback = self.fallback.get_stock_news(symbol, trade_date)
        self._mark_status("stock_news", ok=bool(fallback), data_source="fixture_fallback")
        return fallback

    def _maybe_fallback_f10(self, symbol: str) -> StockF10 | None:
        if not self._should_fallback():
            return None
        if hasattr(self.fallback, "get_stock_f10"):
            fallback = self.fallback.get_stock_f10(symbol)
            self._mark_status("stock_f10", ok=fallback is not None, data_source="fixture_fallback")
            return fallback
        return None

    def _copy_primary_status(self, key: str) -> None:
        status = getattr(self.primary, "provider_status", {}).get(key)
        if status:
            self.provider_status[key] = dict(status)

    def get_market_breadth(self, trade_date: date, at: datetime) -> MarketBreadth | None:
        row = self.primary.get_market_breadth(trade_date, at)
        if row is not None:
            self._copy_primary_status("market_breadth")
            return row
        return self._maybe_fallback_breadth(trade_date, at)

    def get_daily_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        rows = self.primary.get_daily_bars(symbols, end, lookback)
        if any(rows.values()):
            self._copy_primary_status("daily_bars")
            return rows
        return self._maybe_fallback_bars(symbols, end, lookback)

    def get_intraday_bars(self, symbol: str, trade_date: date, interval: str) -> list[IntradayBar]:
        rows = self.primary.get_intraday_bars(symbol, trade_date, interval)
        if rows:
            self._copy_primary_status("intraday_bars")
            return rows
        return self._maybe_fallback_intraday(symbol, trade_date, interval)

    def get_industry_return(self, industry: str, trade_date: date, start: time, end: time) -> Decimal | None:
        value = self.primary.get_industry_return(industry, trade_date, start, end)
        if value is not None:
            self._copy_primary_status("industry_return")
            return value
        return self._maybe_fallback_industry(industry, trade_date, start, end)

    def get_chain_branch_strength(self, trade_date: date, lookback: int) -> list[ChainBranchStrength]:
        rows = self.primary.get_chain_branch_strength(trade_date, lookback)
        if rows:
            self._copy_primary_status("chain_strength")
            return rows
        return self._maybe_fallback_chain_strength(trade_date, lookback)

    def get_stock_news(self, symbol: str, trade_date: date) -> list[StockNews]:
        rows = self.primary.get_stock_news(symbol, trade_date)
        if rows:
            self._copy_primary_status("stock_news")
            return rows
        return self._maybe_fallback_news(symbol, trade_date)

    def get_stock_f10(self, symbol: str) -> StockF10 | None:
        if hasattr(self.primary, "get_stock_f10"):
            row = self.primary.get_stock_f10(symbol)
            if row is not None:
                self._copy_primary_status("stock_f10")
                return row
        return self._maybe_fallback_f10(symbol)

    def get_freshness_info(self) -> dict[str, DataFreshnessInfo]:
        combined: dict[str, DataFreshnessInfo] = {}
        for provider in (self.primary, self.fallback):
            info = getattr(provider, "get_freshness_info", lambda: {})()
            if isinstance(info, dict):
                combined.update(info)
        return combined
