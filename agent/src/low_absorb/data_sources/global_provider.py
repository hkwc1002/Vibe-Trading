"""Global/US market data provider with quality tracking.

Wraps the existing GlobalMarketDataProvider with unified data quality
metadata. The old global_market_provider.py is kept as a compat layer.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any, Callable, Literal

from .models import DataSourceAttempt, MultiSourceFetchResult


class GlobalQualityProvider:
    """Global market provider with quality tracking.

    Delegates to yfinance or Stooq via pluggable ticker/http factories.
    Returns MultiSourceFetchResult with attempt details.
    """

    def __init__(
        self,
        provider: Literal["auto", "yfinance", "stooq"] = "auto",
        ticker_factory: Callable[[str], Any] | None = None,
        http_get: Callable[[str, dict], Any] | None = None,
    ) -> None:
        self._provider = provider
        self._ticker_factory = ticker_factory
        self._http_get = http_get

    def fetch_daily_bars(
        self,
        symbols: list[str],
        end: date,
        lookback: int,
    ) -> dict[str, MultiSourceFetchResult]:
        results: dict[str, MultiSourceFetchResult] = {}
        for symbol in symbols:
            if self._provider == "stooq":
                results[symbol] = self._try_stooq(symbol, end, lookback)
            else:
                yf = self._try_yfinance(symbol, end, lookback)
                if yf.ok:
                    results[symbol] = yf
                elif self._provider == "auto":
                    stooq = self._try_stooq(symbol, end, lookback)
                    stooq.attempts = yf.attempts + stooq.attempts
                    stooq.fallback_used = True
                    results[symbol] = stooq
                else:
                    results[symbol] = MultiSourceFetchResult(
                        ok=False, fail_closed_reason=f"yfinance failed, mode={self._provider}",
                        attempts=yf.attempts,
                    )
        return results

    def _try_yfinance(self, symbol: str, end: date, lookback: int) -> MultiSourceFetchResult:
        started = datetime.now()
        try:
            t = self._ticker_factory(symbol) if self._ticker_factory else __import__("yfinance").Ticker(symbol)
            frame = t.history(period=f"{max(lookback, 5)}d", interval="1d")
            latency = int((datetime.now() - started).total_seconds() * 1000)
            if frame is None or frame.empty:
                return MultiSourceFetchResult(
                    ok=False, attempts=[DataSourceAttempt(source_id=f"yfinance_{symbol}", source_type="yfinance", started_at=started, finished_at=datetime.now(), ok=False, error_message="Empty response", latency_ms=latency)],
                )
            rows = []
            for idx, row in frame.tail(lookback).iterrows():
                td = idx.date() if hasattr(idx, "date") else end
                rows.append({"symbol": symbol, "trade_date": td.isoformat(), "open": float(row.get("Open", 0)), "high": float(row.get("High", 0)), "low": float(row.get("Low", 0)), "close": float(row.get("Close", 0)), "volume": float(row.get("Volume", 0))})
            return MultiSourceFetchResult(
                ok=True, selected_source="yfinance", freshness_seconds=latency // 1000,
                attempts=[DataSourceAttempt(source_id=f"yfinance_{symbol}", source_type="yfinance", started_at=started, finished_at=datetime.now(), ok=True, latency_ms=latency, returned_rows=len(rows))],
                data=rows,
            )
        except Exception as exc:
            return MultiSourceFetchResult(
                ok=False, attempts=[DataSourceAttempt(source_id=f"yfinance_{symbol}", source_type="yfinance", started_at=started, finished_at=datetime.now(), ok=False, error_message=str(exc))],
                fail_closed_reason=str(exc),
            )

    def _try_stooq(self, symbol: str, end: date, lookback: int) -> MultiSourceFetchResult:
        started = datetime.now()
        try:
            url = "https://stooq.com/q/d/l/"
            params: dict = {"s": symbol, "d1": (end - timedelta(days=lookback * 2)).strftime("%Y%m%d"), "d2": end.strftime("%Y%m%d"), "i": "d"}
            if self._http_get is not None:
                text = str(self._http_get(url, params))
            else:
                import requests
                resp = requests.get(url, params=params, timeout=8)
                resp.raise_for_status()
                text = resp.text
            latency = int((datetime.now() - started).total_seconds() * 1000)
            rows = list(csv.DictReader(io.StringIO(text)))
            return MultiSourceFetchResult(
                ok=len(rows) > 0, selected_source="stooq",
                attempts=[DataSourceAttempt(source_id=f"stooq_{symbol}", source_type="stooq", started_at=started, finished_at=datetime.now(), ok=len(rows) > 0, latency_ms=latency, returned_rows=len(rows))],
                data=rows[-lookback:] if rows else None,
            )
        except Exception as exc:
            return MultiSourceFetchResult(
                ok=False, attempts=[DataSourceAttempt(source_id=f"stooq_{symbol}", source_type="stooq", started_at=started, finished_at=datetime.now(), ok=False, error_message=str(exc))],
                fail_closed_reason=str(exc),
            )
