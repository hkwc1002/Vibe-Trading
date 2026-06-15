"""A-share multi-source data adapters.

Each adapter wraps a specific data source and returns normalized results
with quality metadata. All adapters support injection of pluggable
HTTP clients for testability.
"""

from __future__ import annotations

import time as time_module
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AdapterResult:
    """Normalized result from a single adapter fetch."""

    ok: bool
    selected_source: str | None = None
    fall_back_used: bool = False
    latency_ms: int | None = None
    data: Any = None
    error_message: str | None = None
    returned_rows: int | None = None
    freshness_seconds: int | None = None
    is_fixture: bool = False
    attempts: list[dict] = field(default_factory=list)


class BaseAdapter(ABC):
    """Base adapter with timing measurement."""

    def __init__(self) -> None:
        pass

    @property
    @abstractmethod
    def source_id(self) -> str:
        ...

    def _measure(self, fn: Callable, *args, **kwargs) -> tuple[Any, int, str | None]:
        start = time_module.time()
        try:
            result = fn(*args, **kwargs)
            latency = int((time_module.time() - start) * 1000)
            return result, latency, None
        except Exception as exc:
            latency = int((time_module.time() - start) * 1000)
            return None, latency, str(exc)


class TencentAdapter(BaseAdapter):
    """Tencent Finance HTTP API for real-time quotes and indices."""

    def __init__(self, http_get: Callable | None = None) -> None:
        super().__init__()
        self._http_get = http_get

    @property
    def source_id(self) -> str:
        return "tencent"

    def _do_get(self, url: str) -> str:
        if self._http_get is not None:
            return str(self._http_get(url, {}))
        import requests
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        return resp.text

    def fetch_quote(self, symbol: str) -> AdapterResult:
        start = time_module.time()
        try:
            market_prefix = "sh" if symbol and symbol[0] in ("6", "9") else "sz"
            text = self._do_get(f"https://qt.gtimg.cn/q={market_prefix}{symbol}")
            latency = int((time_module.time() - start) * 1000)
            data: dict[str, str | float] = {"raw": text, "market_prefix": market_prefix}
            for line in text.split(";"):
                if "~" in line and "=" in line:
                    parts = line.split("=", 1)[1].strip(' ";\n\r')
                    fields = parts.split("~")
                    if len(fields) >= 4:
                        data["code"] = fields[2] if len(fields) > 2 else symbol
                        for idx, key in [(3, "price"), (4, "close"), (5, "open"), (6, "high"), (7, "low")]:
                            if len(fields) > idx and fields[idx].replace(".", "", 1).lstrip("-").isdigit():
                                data[key] = float(fields[idx])
            return AdapterResult(ok=True, selected_source="tencent", latency_ms=latency, data=data, returned_rows=1)
        except Exception as exc:
            latency = int((time_module.time() - start) * 1000)
            return AdapterResult(ok=False, latency_ms=latency, error_message=str(exc))


class EastmoneyAdapter(BaseAdapter):
    """Eastmoney HTTP API with throttling for sector/flow/news data."""

    def __init__(
        self,
        http_get: Callable | None = None,
        min_interval: float = 1.0,
    ) -> None:
        super().__init__()
        self._http_get = http_get
        self._min_interval = min_interval
        self._last_call = 0.0

    @property
    def source_id(self) -> str:
        return "eastmoney"

    def _throttle(self) -> None:
        wait = self._min_interval - (time_module.time() - self._last_call)
        if wait > 0:
            time_module.sleep(wait)

    def _do_get(self, url: str, params: dict | None = None) -> dict:
        if self._http_get is not None:
            result = self._http_get(url, params or {})
            if isinstance(result, dict):
                return result
            return {}
        import requests
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/",
        })
        resp = session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}

    def fetch_sector_data(self) -> AdapterResult:
        start = time_module.time()
        try:
            self._throttle()
            data = self._do_get(
                "https://push2.eastmoney.com/api/qt/clist/get",
                {
                    "pn": "1", "pz": "500", "po": "1", "np": "1",
                    "fltt": "2", "invt": "2", "fid": "f3",
                    "fs": "m:90+t:3",
                    "fields": "f2,f3,f4,f12,f14",
                },
            )
            self._last_call = time_module.time()
            latency = int((time_module.time() - start) * 1000)
            rows = data.get("data", {}).get("diff", []) if isinstance(data.get("data"), dict) else []
            return AdapterResult(ok=True, selected_source="eastmoney", latency_ms=latency, data=rows, returned_rows=len(rows))
        except Exception as exc:
            latency = int((time_module.time() - start) * 1000)
            return AdapterResult(ok=False, latency_ms=latency, error_message=str(exc))


class MootdxAdapter(BaseAdapter):
    """Mootdx TCP adapter for daily K-line data."""

    def __init__(self, quotes_factory: Callable | None = None) -> None:
        super().__init__()
        self._quotes_factory = quotes_factory

    @property
    def source_id(self) -> str:
        return "mootdx"

    def _get_quotes(self) -> Any:
        if self._quotes_factory is not None:
            return self._quotes_factory()
        from mootdx.quotes import Quotes
        return Quotes.factory(market="std")

    def fetch_kline(self, symbol: str, lookback: int = 20) -> AdapterResult:
        start = time_module.time()
        try:
            client = self._get_quotes()
            market = 1 if symbol.startswith(("6", "9")) else 0
            bars = client.bars(symbol=market, frequency=9, offset=0, start=0, count=lookback)
            latency = int((time_module.time() - start) * 1000)
            if bars is None or bars.empty:
                return AdapterResult(ok=False, latency_ms=latency, error_message="No data from mootdx")
            return AdapterResult(ok=True, selected_source="mootdx", latency_ms=latency, data=bars.to_dict("records"), returned_rows=len(bars))
        except Exception as exc:
            latency = int((time_module.time() - start) * 1000)
            return AdapterResult(ok=False, latency_ms=latency, error_message=str(exc))


class BaiduSinaAdapter(BaseAdapter):
    """Baidu/Sina supplemental K-line adapter via 163 finance API."""

    def __init__(self, http_get: Callable | None = None) -> None:
        super().__init__()
        self._http_get = http_get

    @property
    def source_id(self) -> str:
        return "baidu_sina"

    def _do_get(self, url: str) -> str:
        if self._http_get is not None:
            return str(self._http_get(url, {}))
        import requests
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text

    def fetch_kline(self, symbol: str, lookback: int = 20) -> AdapterResult:
        start = time_module.time()
        try:
            market = 1 if symbol.startswith(("6", "9")) else 0
            today = time_module.time()
            from datetime import date as d_date
            end_str = d_date.fromtimestamp(today).strftime("%Y%m%d")
            url = f"https://quotes.money.163.com/service/chddata.html?code={market}{symbol}&end={end_str}&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP"
            text = self._do_get(url)
            latency = int((time_module.time() - start) * 1000)
            lines = text.strip().split("\n")
            field_names = ["trade_date", "open", "high", "low", "close", "lclose", "chg", "pchg", "turnover", "volume", "amount", "tcap", "mcap"]
            data_rows: list[dict[str, object]] = []
            for line in lines[1:]:  # skip header
                vals = line.split(",")
                if len(vals) >= 11:
                    row: dict[str, object] = {}
                    for i, fn in enumerate(field_names):
                        row[fn] = vals[i] if i < len(vals) else ""
                    data_rows.append(row)
            result_rows = data_rows[-lookback:] if data_rows else []
            # CR-1: freshness from latest trade_date, not request latency
            freshness: int | None = None
            if result_rows:
                lt = result_rows[-1].get("trade_date", "")
                if lt:
                    try:
                        from datetime import datetime as dt
                        market_close = dt.strptime(str(lt), "%Y-%m-%d").replace(hour=15, minute=0, second=0)
                        freshness = max(0, int(time_module.time() - market_close.timestamp()))
                    except (ValueError, OSError, TypeError):
                        freshness = None
            return AdapterResult(
                ok=len(result_rows) > 0, selected_source="baidu_sina",
                latency_ms=latency, data=result_rows,
                returned_rows=len(result_rows), freshness_seconds=freshness,
            )
        except Exception as exc:
            latency = int((time_module.time() - start) * 1000)
            return AdapterResult(ok=False, latency_ms=latency, error_message=str(exc))
