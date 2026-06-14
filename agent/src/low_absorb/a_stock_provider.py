"""A-share market data provider for Low Absorb strategy inputs."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from .data_provider import (
    ChainBranchStrength,
    DailyBar,
    DataFreshnessInfo,
    IntradayBar,
    MarketBreadth,
    ProviderStatusMixin,
    RateLimitedHttpClient,
    StockF10,
    StockNews,
    _decimal,
    _stock_secid,
)
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
        max_data_staleness: int = 60,
    ) -> None:
        self.symbols = symbols or ["601138"]
        self.http_client = http_client or RateLimitedHttpClient()
        self.symbol_industries = {"601138": "服务器ODM"} | (symbol_industries or {})
        self.symbol_names = {"601138": "工业富联"} | (symbol_names or {})
        self.provider_status: dict[str, dict[str, object]] = {}
        self._max_data_staleness = max_data_staleness
        self._latest_captured: dict[str, datetime] = {}

    def _get_json(self, url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        return self.http_client.get_json(url, params)

    def _fetch_limit_break_rate(self) -> Decimal | None:
        """Fetch live limit-break rate from Eastmoney A-share stock list.

        Returns the ratio of 涨停 (limit-up, ≥9.8%) and 跌停 (limit-down,
        ≤-9.8%) stocks to the total A-share universe. Uses a single large
        page request (pz=10000) to cover the full market.

        Returns ``None`` when the endpoint is unavailable, the response is
        invalid, or ``total <= 0`` — callers must treat ``None`` as
        fail-closed (no market breadth data available).
        """
        try:
            data = self._get_json(
                "https://push2.eastmoney.com/api/qt/clist/get",
                {
                    "pn": "1",
                    "pz": "10000",
                    "po": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f3",
                    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                    "fields": "f3",
                },
            )
            rows = data.get("data", {}).get("diff", []) if isinstance(data.get("data"), dict) else []
            total = data.get("data", {}).get("total", 0) if isinstance(data.get("data"), dict) else 0
            if total <= 0 or not isinstance(rows, list):
                return None

            limit_up = 0
            limit_down = 0
            for row in rows:
                if not isinstance(row, dict):
                    continue
                pct = _decimal(row.get("f3"))
                if pct >= Decimal("9.8"):
                    limit_up += 1
                elif pct <= Decimal("-9.8"):
                    limit_down += 1

            return Decimal(str(limit_up + limit_down)) / Decimal(str(total))
        except Exception:
            return None

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
            limit_break_rate = self._fetch_limit_break_rate()
            if limit_break_rate is None:
                self._mark_status(
                    "market_breadth", ok=False, data_source="eastmoney_index",
                    message="limit_break_rate unavailable (clist failed or empty)",
                )
                return None
            self._mark_status("market_breadth", ok=True, data_source="eastmoney_index", staleness_seconds=0, captured_at=at, market_date=trade_date)
            self._latest_captured["market_breadth"] = at
            return MarketBreadth(
                trade_date=trade_date,
                captured_at=at,
                total_market_turnover_cny=turnover,
                limit_break_rate=limit_break_rate,
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
                            captured_at=datetime.combine(trade_day, time(14, 45)),
                        )
                    )
                result[symbol] = rows
            except Exception as exc:
                self._mark_status("daily_bars", ok=False, data_source="eastmoney_kline", message=f"{symbol}: {exc}")
                result[symbol] = []
        if any(result.values()):
            all_bars = [bar for bars in result.values() for bar in bars]
            max_trade_date = max(bar.trade_date for bar in all_bars)
            captured = datetime.combine(max_trade_date, time(14, 45))
            self._mark_status("daily_bars", ok=True, data_source="eastmoney_kline", staleness_seconds=0, market_date=max_trade_date)
            self._latest_captured["daily_bars"] = captured
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
            if bars:
                self._latest_captured["intraday_bars"] = datetime.now()
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
            if news:
                self._latest_captured["stock_news"] = datetime.now()
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
            self._latest_captured["stock_f10"] = datetime.now()
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
        now = datetime.now()
        result: dict[str, DataFreshnessInfo] = {}
        for key, status in self.provider_status.items():
            ok = bool(status.get("ok"))
            staleness = status.get("staleness_seconds")
            captured_at = self._latest_captured.get(key) or status.get("captured_at")
            if not isinstance(captured_at, datetime):
                captured_at = now if ok else None
            market_date = status.get("market_date")
            if isinstance(market_date, date) and captured_at and ok:
                actual_staleness = int((now - captured_at).total_seconds())
                is_stale = actual_staleness > self._max_data_staleness
            else:
                actual_staleness = staleness
                is_stale = not ok or (captured_at is None)
            result[key] = DataFreshnessInfo(
                data_source=str(status.get("data_source", "")),
                captured_at=captured_at,
                market_date=market_date if isinstance(market_date, date) else None,
                staleness_seconds=actual_staleness if isinstance(actual_staleness, int) else None,
                is_stale=is_stale,
                error=status.get("message") if not ok else None,
            )
        return result
