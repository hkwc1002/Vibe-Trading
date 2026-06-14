"""Global/US market data provider for Low Absorb strategy inputs."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Callable, Literal

import requests

from .data_provider import (
    ChainBranchStrength,
    DailyBar,
    DataFreshnessInfo,
    IntradayBar,
    MarketBreadth,
    ProviderStatusMixin,
    StockF10,
    StockNews,
    _decimal,
)
class GlobalMarketDataProvider(ProviderStatusMixin):
    """Free-priority global/US market provider.

    It uses yfinance by default and can fall back to Stooq CSV in auto mode.
    The provider is separate from broker connectors and returns normalized daily
    bars only.
    """

    def __init__(
        self,
        *,
        provider: Literal["auto", "yfinance", "stooq"] = "auto",
        ticker_factory: Callable[[str], Any] | None = None,
        http_get: Callable[[str, dict[str, object]], Any] | None = None,
    ) -> None:
        self.provider = provider
        self._ticker_factory = ticker_factory
        self._http_get = http_get
        self.provider_status: dict[str, dict[str, object]] = {}
        self._latest_captured: dict[str, datetime] = {}

    def _ticker(self, symbol: str) -> Any:
        if self._ticker_factory is not None:
            return self._ticker_factory(symbol)
        import yfinance as yf

        return yf.Ticker(symbol)

    def _stooq_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().lower()
        if "." in normalized:
            return normalized
        return f"{normalized}.us"

    def _get_stooq_csv(self, symbol: str, start: date, end: date) -> str:
        url = "https://stooq.com/q/d/l/"
        params = {
            "s": self._stooq_symbol(symbol),
            "d1": start.strftime("%Y%m%d"),
            "d2": end.strftime("%Y%m%d"),
            "i": "d",
        }
        if self._http_get is not None:
            response = self._http_get(url, params)
        else:
            response = requests.get(url, params=params, timeout=8)
            response.raise_for_status()
        return str(getattr(response, "text", response))

    def get_market_breadth(self, trade_date: date, at: datetime) -> MarketBreadth | None:
        self._mark_status("market_breadth", ok=False, data_source="yfinance", message="not applicable for A-share macro gate")
        return None

    def get_daily_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        if self.provider == "stooq":
            return self._get_stooq_daily_bars(symbols, end, lookback)

        try:
            rows = self._get_yfinance_daily_bars(symbols, end, lookback)
            if self.provider == "auto" and not any(rows.values()):
                return self._get_stooq_daily_bars(symbols, end, lookback)
            return rows
        except Exception as exc:
            self._mark_status("daily_bars", ok=False, data_source="yfinance", message=str(exc))
            if self.provider == "auto":
                return self._get_stooq_daily_bars(symbols, end, lookback)
            return {symbol: [] for symbol in symbols}

    def _get_yfinance_daily_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        result: dict[str, list[DailyBar]] = {}
        for symbol in symbols:
            try:
                frame = self._ticker(symbol).history(period=f"{max(lookback, 5)}d", interval="1d")
                rows: list[DailyBar] = []
                previous_close: Decimal | None = None
                for idx, row in frame.tail(lookback).iterrows():
                    trade_day = idx.date() if hasattr(idx, "date") else end
                    open_price = _decimal(row.get("Open"))
                    high = _decimal(row.get("High"))
                    low = _decimal(row.get("Low"))
                    close = _decimal(row.get("Close"))
                    volume = _decimal(row.get("Volume"))
                    true_range = max(
                        high - low,
                        abs(high - previous_close) if previous_close is not None else high - low,
                        abs(low - previous_close) if previous_close is not None else high - low,
                    )
                    previous_close = close
                    rows.append(
                        DailyBar(
                            symbol=symbol,
                            trade_date=trade_day,
                            open=open_price,
                            high=high,
                            low=low,
                            close=close,
                            volume=volume,
                            atr=true_range if true_range > 0 else Decimal("0.01"),
                            industry="US_EQUITY",
                            stock_name=symbol,
                            captured_at=datetime.combine(trade_day, time(16, 0)),
                        )
                    )
                result[symbol] = rows
            except Exception as exc:
                self._mark_status("daily_bars", ok=False, data_source="yfinance", message=f"{symbol}: {exc}")
                result[symbol] = []
        if any(result.values()):
            self._mark_status("daily_bars", ok=True, data_source="yfinance", staleness_seconds=0)
            self._latest_captured["daily_bars"] = datetime.now()
        return result

    def _get_stooq_daily_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        result: dict[str, list[DailyBar]] = {}
        start = date.fromordinal(max(1, end.toordinal() - max(lookback * 2, 10)))
        for symbol in symbols:
            try:
                text = self._get_stooq_csv(symbol, start, end)
                rows: list[DailyBar] = []
                previous_close: Decimal | None = None
                for row in list(csv.DictReader(io.StringIO(text)))[-lookback:]:
                    trade_day = date.fromisoformat(str(row.get("Date")))
                    open_price = _decimal(row.get("Open"))
                    high = _decimal(row.get("High"))
                    low = _decimal(row.get("Low"))
                    close = _decimal(row.get("Close"))
                    volume = _decimal(row.get("Volume"))
                    true_range = max(
                        high - low,
                        abs(high - previous_close) if previous_close is not None else high - low,
                        abs(low - previous_close) if previous_close is not None else high - low,
                    )
                    previous_close = close
                    rows.append(
                        DailyBar(
                            symbol=symbol,
                            trade_date=trade_day,
                            open=open_price,
                            high=high,
                            low=low,
                            close=close,
                            volume=volume,
                            atr=true_range if true_range > 0 else Decimal("0.01"),
                            industry="US_EQUITY",
                            stock_name=symbol,
                            captured_at=datetime.combine(trade_day, time(16, 0)),
                        )
                    )
                result[symbol] = rows
            except Exception as exc:
                self._mark_status("daily_bars", ok=False, data_source="stooq", message=f"{symbol}: {exc}")
                result[symbol] = []
        if any(result.values()):
            self._mark_status("daily_bars", ok=True, data_source="stooq", staleness_seconds=0)
            self._latest_captured["daily_bars"] = datetime.now()
        return result

    def get_intraday_bars(self, symbol: str, trade_date: date, interval: str) -> list[IntradayBar]:
        self._mark_status("intraday_bars", ok=False, data_source="yfinance", message="not used by Low Absorb")
        return []

    def get_industry_return(self, industry: str, trade_date: date, start: time, end: time) -> Decimal | None:
        return None

    def get_chain_branch_strength(self, trade_date: date, lookback: int) -> list[ChainBranchStrength]:
        return []

    def get_stock_news(self, symbol: str, trade_date: date) -> list[StockNews]:
        self._mark_status("stock_news", ok=False, data_source="yfinance", message="news not available via global provider")
        return []

    def get_stock_f10(self, symbol: str) -> StockF10 | None:
        self._mark_status("stock_f10", ok=False, data_source="yfinance", message="f10 not available via global provider")
        return None

    def get_freshness_info(self) -> dict[str, DataFreshnessInfo]:
        now = datetime.now()
        result: dict[str, DataFreshnessInfo] = {}
        for key, status in self.provider_status.items():
            ok = bool(status.get("ok"))
            staleness = status.get("staleness_seconds")
            captured_at = self._latest_captured.get(key)
            market_date = status.get("market_date")
            if captured_at and ok and isinstance(market_date, date):
                actual_staleness = int((now - captured_at).total_seconds())
                is_stale = actual_staleness > 60
            elif captured_at and ok:
                actual_staleness = int((now - captured_at).total_seconds())
                is_stale = actual_staleness > 300
            else:
                actual_staleness = staleness
                is_stale = not ok
            result[key] = DataFreshnessInfo(
                data_source=str(status.get("data_source", "")),
                captured_at=captured_at,
                market_date=market_date if isinstance(market_date, date) else None,
                staleness_seconds=actual_staleness if isinstance(actual_staleness, int) else None,
                is_stale=is_stale,
                error=status.get("message") if not ok else None,
            )
        return result
