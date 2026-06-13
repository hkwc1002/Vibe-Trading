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
    ) -> None:
        self.provider_status[key] = {
            "ok": ok,
            "data_source": data_source,
            "message": message,
            "staleness_seconds": staleness_seconds,
        }


class AStockLowAbsorbProvider(ProviderStatusMixin):
    """A-share Python data provider based on public market endpoints.

    The implementation follows the a-stock-data preference: Tencent and Eastmoney
    public HTTP endpoints, with Eastmoney requests serialized through a throttled
    client. It is read-only and never connects to broker execution systems.
    """

    def __init__(
        self,
        *,
        symbols: list[str] | None = None,
        http_client: RateLimitedHttpClient | None = None,
        symbol_industries: dict[str, str] | None = None,
        symbol_names: dict[str, str] | None = None,
    ) -> None:
        self.symbols = symbols or ["601138"]
        self.http_client = http_client or RateLimitedHttpClient()
        self.symbol_industries = {"601138": "服务器ODM"} | (symbol_industries or {})
        self.symbol_names = {"601138": "工业富联"} | (symbol_names or {})
        self.provider_status: dict[str, dict[str, object]] = {}

    def _get_json(self, url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        return self.http_client.get_json(url, params)

    def get_market_breadth(self, trade_date: date, at: datetime) -> MarketBreadth | None:
        try:
            data = self._get_json(
                "https://push2.eastmoney.com/api/qt/ulist.np/get",
                {
                    "fltt": "2",
                    "invt": "2",
                    "fields": "f3,f6",
                    "secids": "1.000001,0.399001",
                },
            )
            rows = data.get("data", {}).get("diff", []) if isinstance(data.get("data"), dict) else []
            turnover = sum(_decimal(row.get("f6")) for row in rows if isinstance(row, dict))
            if turnover <= 0:
                self._mark_status("market_breadth", ok=False, data_source="eastmoney_index", message="empty turnover")
                return None
            self._mark_status("market_breadth", ok=True, data_source="eastmoney_index", staleness_seconds=0)
            return MarketBreadth(
                trade_date=trade_date,
                captured_at=at,
                total_market_turnover_cny=turnover,
                limit_break_rate=Decimal("0.20"),
            )
        except Exception as exc:
            self._mark_status("market_breadth", ok=False, data_source="eastmoney_index", message=str(exc))
            return None

    def get_daily_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        result: dict[str, list[DailyBar]] = {}
        for symbol in symbols:
            try:
                data = self._get_json(
                    "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                    {
                        "secid": _stock_secid(symbol),
                        "klt": "101",
                        "fqt": "1",
                        "beg": "19900101",
                        "end": end.strftime("%Y%m%d"),
                        "lmt": str(lookback),
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    },
                )
                klines = data.get("data", {}).get("klines", []) if isinstance(data.get("data"), dict) else []
                rows: list[DailyBar] = []
                previous_close: Decimal | None = None
                for raw in klines[-lookback:]:
                    parts = str(raw).split(",")
                    if len(parts) < 6:
                        continue
                    trade_day = date.fromisoformat(parts[0])
                    open_price = _decimal(parts[1])
                    close = _decimal(parts[2])
                    high = _decimal(parts[3])
                    low = _decimal(parts[4])
                    volume = _decimal(parts[5])
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
                            industry=self.symbol_industries.get(symbol, "未分类"),
                            stock_name=self.symbol_names.get(symbol, symbol),
                            captured_at=datetime.combine(end, time(14, 45)),
                        )
                    )
                result[symbol] = rows
            except Exception as exc:
                self._mark_status("daily_bars", ok=False, data_source="eastmoney_kline", message=f"{symbol}: {exc}")
                result[symbol] = []
        if any(result.values()):
            self._mark_status("daily_bars", ok=True, data_source="eastmoney_kline", staleness_seconds=0)
        return result

    def get_intraday_bars(self, symbol: str, trade_date: date, interval: str) -> list[IntradayBar]:
        try:
            data = self._get_json(
                "https://push2his.eastmoney.com/api/qt/stock/trends2/get",
                {
                    "secid": _stock_secid(symbol),
                    "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                    "iscr": "0",
                    "iscca": "0",
                },
            )
            trends = data.get("data", {}).get("trends", []) if isinstance(data.get("data"), dict) else []
            bars: list[IntradayBar] = []
            for raw in trends:
                parts = str(raw).split(",")
                if len(parts) < 3 or not parts[0].startswith(trade_date.isoformat()):
                    continue
                at = datetime.strptime(parts[0], "%Y-%m-%d %H:%M")
                price = _decimal(parts[1])
                volume = _decimal(parts[2])
                bars.append(
                    IntradayBar(
                        symbol=symbol,
                        trade_date=trade_date,
                        at=at,
                        open=price,
                        high=price,
                        low=price,
                        close=price,
                        volume=volume,
                    )
                )
            self._mark_status("intraday_bars", ok=bool(bars), data_source="eastmoney_trends", staleness_seconds=0)
            return bars
        except Exception as exc:
            self._mark_status("intraday_bars", ok=False, data_source="eastmoney_trends", message=str(exc))
            return []

    def get_industry_return(self, industry: str, trade_date: date, start: time, end: time) -> Decimal | None:
        self._mark_status("industry_return", ok=False, data_source="not_configured", message="industry intraday return unavailable")
        return None

    def get_chain_branch_strength(self, trade_date: date, lookback: int) -> list[ChainBranchStrength]:
        self._mark_status("chain_strength", ok=False, data_source="not_configured", message="chain branch strength needs sector mapping")
        return []

    def get_stock_news(self, symbol: str, trade_date: date) -> list[StockNews]:
        try:
            data = self._get_json(
                "https://push2.eastmoney.com/api/qt/stock/news",
                {"secid": _stock_secid(symbol), "count": "10"},
            )
            items = data.get("data", []) if isinstance(data.get("data"), list) else []
            news: list[StockNews] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "") or "")
                if not title:
                    continue
                news.append(
                    StockNews(
                        news_id=str(item.get("id", "")),
                        symbol=symbol,
                        title=title,
                        summary=str(item.get("intro", "") or ""),
                        source=str(item.get("source", "") or ""),
                        published_at=datetime.fromisoformat(item["date"]) if isinstance(item.get("date"), str) and item["date"] else None,
                        captured_at=datetime.now(),
                        sentiment="neutral",
                        url=str(item.get("url", "") or ""),
                    )
                )
            self._mark_status("stock_news", ok=bool(news), data_source="eastmoney_news", staleness_seconds=0)
            return news
        except Exception as exc:
            self._mark_status("stock_news", ok=False, data_source="eastmoney_news", message=str(exc))
            return []

    def get_stock_f10(self, symbol: str) -> StockF10 | None:
        try:
            data = self._get_json(
                "https://push2.eastmoney.com/api/qt/stock/get",
                {
                    "secid": _stock_secid(symbol),
                    "fields": "f57,f58,f84,f85,f86,f162,f167,f168,f169,f170",
                },
            )
            row = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
            if not row.get("f57"):
                self._mark_status("stock_f10", ok=False, data_source="eastmoney_quote", message="empty f10 response")
                return None
            self._mark_status("stock_f10", ok=True, data_source="eastmoney_quote", staleness_seconds=0)
            return StockF10(
                symbol=symbol,
                total_shares=_decimal(row.get("f84")),
                circulating_shares=_decimal(row.get("f85")),
                pe_ttm=_decimal(row.get("f162")),
                pb_ratio=_decimal(row.get("f167")),
                roe_ttm=_decimal(row.get("f169")),
                industry=str(row.get("f57", "")),
                main_business="",
                captured_at=datetime.now(),
            )
        except Exception as exc:
            self._mark_status("stock_f10", ok=False, data_source="eastmoney_quote", message=str(exc))
            return None

    def get_freshness_info(self) -> dict[str, DataFreshnessInfo]:
        result: dict[str, DataFreshnessInfo] = {}
        for key, status in self.provider_status.items():
            ok = bool(status.get("ok"))
            result[key] = DataFreshnessInfo(
                data_source=str(status.get("data_source", "")),
                captured_at=datetime.now(),
                staleness_seconds=status.get("staleness_seconds"),
                is_stale=not ok,
                error=status.get("message") if not ok else None,
            )
        return result


class FallbackMarketDataProvider(ProviderStatusMixin):
    """Use a Python provider first and fixture data only when the provider is empty."""

    def __init__(self, *, primary: MarketDataProvider, fallback: MarketDataProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.symbols = list(getattr(primary, "symbols", []) or getattr(fallback, "symbols", []))
        self.provider_status: dict[str, dict[str, object]] = {}

    def _copy_primary_status(self, key: str) -> None:
        status = getattr(self.primary, "provider_status", {}).get(key)
        if status:
            self.provider_status[key] = dict(status)

    def get_market_breadth(self, trade_date: date, at: datetime) -> MarketBreadth | None:
        row = self.primary.get_market_breadth(trade_date, at)
        if row is not None:
            self._copy_primary_status("market_breadth")
            return row
        fallback = self.fallback.get_market_breadth(trade_date, at)
        self._mark_status("market_breadth", ok=fallback is not None, data_source="fixture_fallback")
        return fallback

    def get_daily_bars(self, symbols: list[str], end: date, lookback: int) -> dict[str, list[DailyBar]]:
        rows = self.primary.get_daily_bars(symbols, end, lookback)
        if any(rows.values()):
            self._copy_primary_status("daily_bars")
            return rows
        fallback = self.fallback.get_daily_bars(symbols, end, lookback)
        self._mark_status("daily_bars", ok=any(fallback.values()), data_source="fixture_fallback")
        return fallback

    def get_intraday_bars(self, symbol: str, trade_date: date, interval: str) -> list[IntradayBar]:
        rows = self.primary.get_intraday_bars(symbol, trade_date, interval)
        if rows:
            self._copy_primary_status("intraday_bars")
            return rows
        fallback = self.fallback.get_intraday_bars(symbol, trade_date, interval)
        self._mark_status("intraday_bars", ok=bool(fallback), data_source="fixture_fallback")
        return fallback

    def get_industry_return(self, industry: str, trade_date: date, start: time, end: time) -> Decimal | None:
        value = self.primary.get_industry_return(industry, trade_date, start, end)
        if value is not None:
            self._copy_primary_status("industry_return")
            return value
        fallback = self.fallback.get_industry_return(industry, trade_date, start, end)
        self._mark_status("industry_return", ok=fallback is not None, data_source="fixture_fallback")
        return fallback

    def get_chain_branch_strength(self, trade_date: date, lookback: int) -> list[ChainBranchStrength]:
        rows = self.primary.get_chain_branch_strength(trade_date, lookback)
        if rows:
            self._copy_primary_status("chain_strength")
            return rows
        fallback = self.fallback.get_chain_branch_strength(trade_date, lookback)
        self._mark_status("chain_strength", ok=bool(fallback), data_source="fixture_fallback")
        return fallback

    def get_stock_news(self, symbol: str, trade_date: date) -> list[StockNews]:
        rows = self.primary.get_stock_news(symbol, trade_date)
        if rows:
            self._copy_primary_status("stock_news")
            return rows
        fallback = self.fallback.get_stock_news(symbol, trade_date)
        self._mark_status("stock_news", ok=bool(fallback), data_source="fixture_fallback")
        return fallback

    def get_stock_f10(self, symbol: str) -> StockF10 | None:
        if hasattr(self.primary, "get_stock_f10"):
            row = self.primary.get_stock_f10(symbol)
            if row is not None:
                self._copy_primary_status("stock_f10")
                return row
        if hasattr(self.fallback, "get_stock_f10"):
            fallback = self.fallback.get_stock_f10(symbol)
            self._mark_status("stock_f10", ok=fallback is not None, data_source="fixture_fallback")
            return fallback
        return None

    def get_freshness_info(self) -> dict[str, DataFreshnessInfo]:
        combined: dict[str, DataFreshnessInfo] = {}
        for provider in (self.primary, self.fallback):
            info = getattr(provider, "get_freshness_info", lambda: {})()
            if isinstance(info, dict):
                combined.update(info)
        return combined


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
                            captured_at=datetime.combine(end, time(16, 0)),
                        )
                    )
                result[symbol] = rows
            except Exception as exc:
                self._mark_status("daily_bars", ok=False, data_source="yfinance", message=f"{symbol}: {exc}")
                result[symbol] = []
        if any(result.values()):
            self._mark_status("daily_bars", ok=True, data_source="yfinance", staleness_seconds=0)
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
                            captured_at=datetime.combine(end, time(16, 0)),
                        )
                    )
                result[symbol] = rows
            except Exception as exc:
                self._mark_status("daily_bars", ok=False, data_source="stooq", message=f"{symbol}: {exc}")
                result[symbol] = []
        if any(result.values()):
            self._mark_status("daily_bars", ok=True, data_source="stooq", staleness_seconds=0)
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
        result: dict[str, DataFreshnessInfo] = {}
        for key, status in self.provider_status.items():
            ok = bool(status.get("ok"))
            result[key] = DataFreshnessInfo(
                data_source=str(status.get("data_source", "")),
                staleness_seconds=status.get("staleness_seconds"),
                is_stale=not ok,
                error=status.get("message") if not ok else None,
            )
        return result
