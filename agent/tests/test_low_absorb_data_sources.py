from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.api import register_low_absorb_routes
from src.low_absorb.api.workbench import set_workbench_storage
from src.low_absorb.data_provider import (
    AStockLowAbsorbProvider,
    ChainBranchStrength,
    DailyBar,
    DataFreshnessInfo,
    FallbackMarketDataProvider,
    FixtureMarketDataProvider,
    GlobalMarketDataProvider,
    MarketBreadth,
    StockF10,
    StockNews,
)
from src.low_absorb.storage import InMemoryLowAbsorbStorage


SCAN_AT = datetime(2026, 6, 12, 14, 45)


def _qualified_bars(symbol: str = "601138") -> list[DailyBar]:
    rows: list[DailyBar] = []
    start = date(2026, 6, 12) - timedelta(days=25)
    for idx in range(19):
        rows.append(
            DailyBar(
                symbol=symbol,
                trade_date=start + timedelta(days=idx),
                open=Decimal("20.00"),
                high=Decimal("20.40"),
                low=Decimal("19.80"),
                close=Decimal("20.00"),
                volume=Decimal("1000000"),
                atr=Decimal("1.00"),
                industry="服务器ODM",
                stock_name="工业富联",
                captured_at=SCAN_AT,
            )
        )
    rows.append(
        DailyBar(
            symbol=symbol,
            trade_date=date(2026, 6, 12),
            open=Decimal("20.30"),
            high=Decimal("20.55"),
            low=Decimal("19.50"),
            close=Decimal("20.12"),
            volume=Decimal("600000"),
            atr=Decimal("1.00"),
            industry="服务器ODM",
            stock_name="工业富联",
            captured_at=SCAN_AT,
        )
    )
    return rows


def test_a_stock_provider_parses_eastmoney_daily_bars() -> None:
    provider = AStockLowAbsorbProvider(symbols=["601138"])

    def fake_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        assert "push2his.eastmoney.com" in url
        return {
            "data": {
                "klines": [
                    "2026-06-10,20.00,20.20,20.40,19.90,1000000,20000000,0,0,0,0",
                    "2026-06-11,20.10,20.00,20.30,19.80,1000000,20000000,0,0,0,0",
                    "2026-06-12,20.30,20.12,20.55,19.50,600000,12000000,0,0,0,0",
                ]
            }
        }

    provider._get_json = fake_json  # type: ignore[method-assign]

    rows = provider.get_daily_bars(["601138"], date(2026, 6, 12), lookback=3)["601138"]

    assert len(rows) == 3
    assert rows[-1].symbol == "601138"
    assert rows[-1].stock_name == "工业富联"
    assert rows[-1].industry == "服务器ODM"
    assert rows[-1].close == Decimal("20.12")
    assert rows[-1].atr > 0
    assert rows[-1].captured_at == datetime(2026, 6, 12, 14, 45)
    assert provider.provider_status["daily_bars"]["data_source"] == "eastmoney_kline"


def test_a_stock_provider_daily_bar_captured_at_matches_trade_day() -> None:
    provider = AStockLowAbsorbProvider(symbols=["601138"])

    def fake_old_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "data": {
                "klines": [
                    "2026-06-09,20.00,20.20,20.40,19.90,1000000,20000000,0,0,0,0",
                    "2026-06-10,20.10,20.00,20.30,19.80,1000000,20000000,0,0,0,0",
                ]
            }
        }

    provider._get_json = fake_old_json  # type: ignore[method-assign]
    rows = provider.get_daily_bars(["601138"], date(2026, 6, 12), lookback=2)["601138"]

    assert len(rows) == 2
    assert rows[0].captured_at == datetime(2026, 6, 9, 14, 45)
    assert rows[1].captured_at == datetime(2026, 6, 10, 14, 45)
    assert rows[1].captured_at < datetime(2026, 6, 12, 14, 45)


def test_a_stock_provider_old_daily_bars_trigger_scanner_fail_closed() -> None:
    from src.low_absorb.config import LowAbsorbConfig
    from src.low_absorb.scanner import LowAbsorbScanner

    provider = AStockLowAbsorbProvider(symbols=["601138"], max_data_staleness=60)

    def fake_breadth_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        if "clist" in url:
            diff = [{"f3": 10.0}, {"f3": 9.9}, {"f3": -10.0}, {"f3": 5.0}]
            return {"data": {"total": len(diff), "diff": diff}}
        return {"data": {"diff": [{"f3": 0.5, "f6": 900000000000}]}}

    def fake_old_kline_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "data": {
                "klines": [
                    "2026-06-10,20.00,20.20,20.40,19.90,1000000,20000000,0,0,0,0",
                ]
            }
        }

    def fake_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        if "kline" in url:
            return fake_old_kline_json(url, params)
        return fake_breadth_json(url, params)

    provider._get_json = fake_json  # type: ignore[method-assign]
    config = LowAbsorbConfig(max_data_staleness_seconds=60)
    scanner = LowAbsorbScanner(provider, config)
    result = scanner.scan_tail_session_with_signals(
        date(2026, 6, 12),
        at=datetime(2026, 6, 12, 14, 45),
        symbols=["601138"],
    )
    assert len(result.signals) == 0
    assert len(result.trade_plans) == 0


def test_a_stock_provider_clist_failure_fails_closed() -> None:
    """H1: When clist endpoint fails, get_market_breadth returns None (fail-closed)."""
    provider = AStockLowAbsorbProvider(symbols=["601138"])

    def fake_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        if "clist" in url:
            raise ConnectionError("Eastmoney clist unavailable")
        return {"data": {"diff": [{"f3": 0.5, "f6": 900000000000}]}}

    provider._get_json = fake_json  # type: ignore[method-assign]
    breadth = provider.get_market_breadth(date(2026, 6, 12), SCAN_AT)

    assert breadth is None
    assert provider.provider_status["market_breadth"]["ok"] is False
    assert "limit_break" in str(provider.provider_status["market_breadth"]["message"]).lower() or "clist" in str(provider.provider_status["market_breadth"]["message"]).lower()


def test_a_stock_provider_partial_clist_response_fails_closed() -> None:
    """When Eastmoney returns fewer rows than total, limit_break_rate is None (fail-closed)."""
    provider = AStockLowAbsorbProvider(symbols=["601138"])
    request_count = 0

    def fake_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        nonlocal request_count
        if "clist" in url:
            request_count += 1
            pn = int((params or {}).get("pn", 1))
            if pn == 1:
                # total=5000 but only return 100 rows (truncated first page)
                return {"data": {"total": 5000, "diff": [{"f3": 10.0}] * 100}}
            # Subsequent pages return empty — total never reached
            return {"data": {"total": 5000, "diff": []}}
        return {"data": {"diff": [{"f3": 0.5, "f6": 900000000000}]}}

    provider._get_json = fake_json  # type: ignore[method-assign]
    breadth = provider.get_market_breadth(date(2026, 6, 12), SCAN_AT)

    assert breadth is None, "Partial clist response must fail-closed"
    assert provider.provider_status["market_breadth"]["ok"] is False
    assert request_count >= 2, "Should have paginated before concluding truncation"


def test_high_limit_break_rate_triggers_macro_fuse() -> None:
    """H2: When limit_break_rate exceeds threshold, breadth passes but scanner blocks."""
    from src.low_absorb.config import LowAbsorbConfig
    from src.low_absorb.scanner import LowAbsorbScanner

    # Simulate a day with 52% limit break rate (many stocks at limit up/down)
    total_stocks = 100
    limit_break_stocks = 52
    normal_stocks = total_stocks - limit_break_stocks
    diff = [{"f3": 10.0}] * limit_break_stocks + [{"f3": 1.0}] * normal_stocks

    provider = AStockLowAbsorbProvider(symbols=["601138"])

    def fake_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        if "clist" in url:
            return {"data": {"total": total_stocks, "diff": diff}}
        return {"data": {"diff": [{"f3": 0.5, "f6": 900000000000}]}}

    provider._get_json = fake_json  # type: ignore[method-assign]
    config = LowAbsorbConfig(max_data_staleness_seconds=60, max_limit_break_rate=Decimal("0.45"))
    scanner = LowAbsorbScanner(provider, config)

    breadth = provider.get_market_breadth(date(2026, 6, 12), SCAN_AT)
    assert breadth is not None
    assert breadth.limit_break_rate == Decimal("0.52")

    # market_breadth_gate_passed should reject: 0.52 >= 0.45
    from src.low_absorb.sentiment import market_breadth_gate_passed
    assert market_breadth_gate_passed(breadth, config=config, at=SCAN_AT) is False


def test_fallback_provider_records_fixture_fallback_status() -> None:
    fallback = FixtureMarketDataProvider(
        symbols=["601138"],
        market_breadth=MarketBreadth(
            trade_date=date(2026, 6, 12),
            captured_at=SCAN_AT,
            total_market_turnover_cny=Decimal("600000000000"),
            limit_break_rate=Decimal("0.20"),
        ),
        daily_bars={"601138": _qualified_bars()},
        chain_strength=[
            ChainBranchStrength(
                branch_name="服务器ODM",
                rank=1,
                total_branches=1,
                slope=Decimal("0.08"),
                relative_strength=Decimal("1.20"),
            )
        ],
    )
    provider = FallbackMarketDataProvider(primary=AStockLowAbsorbProvider(symbols=["601138"]), fallback=fallback)
    provider.primary.get_market_breadth = lambda trade_date, at: None  # type: ignore[method-assign]

    breadth = provider.get_market_breadth(date(2026, 6, 12), SCAN_AT)

    assert breadth is not None
    assert provider.provider_status["market_breadth"]["data_source"] == "fixture_fallback"
    assert provider.provider_status["market_breadth"]["ok"] is True


def test_scan_tail_api_returns_provider_status_when_using_python_provider() -> None:
    storage = InMemoryLowAbsorbStorage()
    fixture = FixtureMarketDataProvider(
        symbols=["601138"],
        market_breadth=MarketBreadth(
            trade_date=date(2026, 6, 12),
            captured_at=SCAN_AT,
            total_market_turnover_cny=Decimal("600000000000"),
            limit_break_rate=Decimal("0.20"),
        ),
        daily_bars={"601138": _qualified_bars()},
        chain_strength=[
            ChainBranchStrength(
                branch_name="服务器ODM",
                rank=1,
                total_branches=1,
                slope=Decimal("0.08"),
                relative_strength=Decimal("1.20"),
            )
        ],
    )
    provider = FallbackMarketDataProvider(primary=AStockLowAbsorbProvider(symbols=["601138"]), fallback=fixture)
    provider.primary.get_market_breadth = lambda trade_date, at: fixture.get_market_breadth(trade_date, at)  # type: ignore[method-assign]
    provider.primary.get_daily_bars = lambda symbols, end, lookback: fixture.get_daily_bars(symbols, end, lookback)  # type: ignore[method-assign]
    provider.primary.get_intraday_bars = lambda symbol, trade_date, interval: fixture.get_intraday_bars(symbol, trade_date, interval)  # type: ignore[method-assign]
    provider.primary.get_chain_branch_strength = lambda trade_date, lookback: fixture.get_chain_branch_strength(trade_date, lookback)  # type: ignore[method-assign]
    provider.primary.provider_status = {"daily_bars": {"ok": True, "data_source": "eastmoney_kline"}}  # type: ignore[attr-defined]
    set_workbench_storage(storage, data_provider=provider)
    app = FastAPI()
    register_low_absorb_routes(app)
    client = TestClient(app)

    response = client.post("/low-absorb/scan-tail", json={"trade_date": "2026-06-12", "at": SCAN_AT.isoformat()})

    assert response.status_code == 200
    body = response.json()
    assert body["provider_status"]["daily_bars"]["data_source"] == "eastmoney_kline"
    assert body["data_source"] == "fixture_fallback"


def test_global_market_provider_parses_yfinance_history() -> None:
    class FakeTicker:
        def history(self, period: str = "5d", interval: str = "1d"):
            import pandas as pd

            return pd.DataFrame(
                [
                    {"Open": 100, "High": 102, "Low": 99, "Close": 101, "Volume": 1000},
                    {"Open": 101, "High": 103, "Low": 100, "Close": 102, "Volume": 1200},
                ],
                index=pd.to_datetime(["2026-06-11", "2026-06-12"]),
            )

    provider = GlobalMarketDataProvider(ticker_factory=lambda symbol: FakeTicker())

    rows = provider.get_daily_bars(["NVDA"], date(2026, 6, 12), lookback=2)["NVDA"]

    assert len(rows) == 2
    assert rows[-1].close == Decimal("102")
    assert rows[-1].industry == "US_EQUITY"
    assert provider.provider_status["daily_bars"]["data_source"] == "yfinance"


def test_global_market_provider_parses_stooq_csv() -> None:
    class FakeResponse:
        text = "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-06-11,100,102,99,101,1000",
                "2026-06-12,101,103,100,102,1200",
            ]
        )

    provider = GlobalMarketDataProvider(provider="stooq", http_get=lambda url, params: FakeResponse())

    rows = provider.get_daily_bars(["NVDA"], date(2026, 6, 12), lookback=2)["NVDA"]

    assert len(rows) == 2
    assert rows[-1].close == Decimal("102")
    assert rows[-1].atr == Decimal("3")
    assert rows[-1].industry == "US_EQUITY"
    assert provider.provider_status["daily_bars"]["data_source"] == "stooq"


def test_global_market_provider_auto_falls_back_to_stooq_when_yfinance_empty() -> None:
    class FakeResponse:
        text = "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-06-12,101,103,100,102,1200",
            ]
        )

    class EmptyTicker:
        def history(self, period: str = "5d", interval: str = "1d"):
            import pandas as pd

            return pd.DataFrame([])

    provider = GlobalMarketDataProvider(
        provider="auto",
        ticker_factory=lambda symbol: EmptyTicker(),
        http_get=lambda url, params: FakeResponse(),
    )

    rows = provider.get_daily_bars(["NVDA"], date(2026, 6, 12), lookback=1)["NVDA"]

    assert rows[-1].close == Decimal("102")
    assert provider.provider_status["daily_bars"]["data_source"] == "stooq"


def test_a_stock_provider_returns_stock_news() -> None:
    provider = AStockLowAbsorbProvider(symbols=["601138"])

    def fake_news_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "data": [
                {"id": "n1", "title": "工业富联AI服务器订单增长", "intro": "订单增长显著", "source": "东方财富", "date": "2026-06-12 10:00:00"},
                {"id": "n2", "title": "GB300量产预期带动产业链", "intro": "产业链受益明显", "source": "东方财富", "date": "2026-06-12 11:00:00"},
            ]
        }

    provider._get_json = fake_news_json  # type: ignore[method-assign]
    news = provider.get_stock_news("601138", date(2026, 6, 12))

    assert len(news) == 2
    assert news[0].title == "工业富联AI服务器订单增长"
    assert news[0].source == "东方财富"
    assert provider.provider_status["stock_news"]["ok"] is True


def test_a_stock_provider_returns_f10() -> None:
    provider = AStockLowAbsorbProvider(symbols=["601138"])

    def fake_f10_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "data": {
                "f57": "601138",
                "f84": "10000000000",
                "f85": "5000000000",
                "f162": "25.5",
                "f167": "3.2",
                "f169": "0.15",
            }
        }

    provider._get_json = fake_f10_json  # type: ignore[method-assign]
    f10 = provider.get_stock_f10("601138")

    assert f10 is not None
    assert f10.symbol == "601138"
    assert f10.pe_ttm == Decimal("25.5")
    assert f10.pb_ratio == Decimal("3.2")
    assert f10.roe_ttm == Decimal("0.15")
    assert provider.provider_status["stock_f10"]["ok"] is True


def test_a_stock_provider_freshness_info_reflects_status() -> None:
    provider = AStockLowAbsorbProvider(symbols=["601138"])
    provider.provider_status["daily_bars"] = {"ok": True, "data_source": "eastmoney_kline", "staleness_seconds": 0}

    info = provider.get_freshness_info()

    assert "daily_bars" in info
    assert info["daily_bars"].data_source == "eastmoney_kline"
    assert info["daily_bars"].is_stale is False


def test_fixture_provider_stock_news_returns_empty() -> None:
    provider = FixtureMarketDataProvider()
    news = provider.get_stock_news("601138", date(2026, 6, 12))
    assert news == []
    assert provider.get_freshness_info() == {}


# ──────────────────────────────────────────────────────────────────────────────
# Task 1: A-share data-source fail-closed and freshness tests
# ──────────────────────────────────────────────────────────────────────────────


def test_a_stock_provider_normal_operation_breadth_and_freshness() -> None:
    """Normal operation: breadth parsed, limit_break_rate computed from full-market clist data."""
    provider = AStockLowAbsorbProvider(symbols=["601138"])

    # Simulate full coverage: total matches len(diff) so pagination succeeds
    clist_diff = [
        {"f3": 10.0}, {"f3": 9.9}, {"f3": 8.0}, {"f3": -10.0},
        {"f3": 5.0}, {"f3": 2.0}, {"f3": -3.0},
    ]

    def fake_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        if "clist" in url:
            return {"data": {"total": len(clist_diff), "diff": clist_diff}}
        if "ulist" in url:
            return {"data": {"diff": [{"f3": 0.5, "f6": 850000000000}]}}
        return {"data": {}}

    provider._get_json = fake_json  # type: ignore[method-assign]

    breadth = provider.get_market_breadth(date(2026, 6, 12), SCAN_AT)

    assert breadth is not None
    assert breadth.total_market_turnover_cny == Decimal("850000000000")
    # limit_break_rate = (3 limit_up + 1 limit_down) / 7
    assert breadth.limit_break_rate > 0
    assert breadth.limit_break_rate < Decimal("1")
    assert provider.provider_status["market_breadth"]["ok"] is True


def test_a_stock_provider_freshness_info_structure_when_data_is_fresh() -> None:
    """get_freshness_info returns complete DataFreshnessInfo for fresh data."""
    provider = AStockLowAbsorbProvider(symbols=["601138"])
    now = datetime.now()
    today = now.date()
    provider.provider_status = {
        "daily_bars": {
            "ok": True,
            "data_source": "eastmoney_kline",
            "staleness_seconds": 0,
            "captured_at": now,
            "market_date": today,
        },
        "market_breadth": {
            "ok": True,
            "data_source": "eastmoney_index",
            "staleness_seconds": 0,
            "captured_at": now,
            "market_date": today,
        },
    }
    provider._latest_captured = {"daily_bars": now, "market_breadth": now}

    info = provider.get_freshness_info()

    assert set(info.keys()) == {"daily_bars", "market_breadth"}
    for key in ("daily_bars", "market_breadth"):
        fi = info[key]
        assert fi.data_source != ""
        assert fi.captured_at is not None
        assert fi.market_date == today
        assert fi.is_stale is False
        assert fi.error is None


def test_a_stock_provider_api_failure_returns_error_freshness() -> None:
    """When the Eastmoney API raises, provider returns None and records the error."""
    provider = AStockLowAbsorbProvider(symbols=["601138"])

    def failing_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        raise ConnectionError("Eastmoney unreachable")

    provider._get_json = failing_json  # type: ignore[method-assign]

    breadth = provider.get_market_breadth(date(2026, 6, 12), SCAN_AT)
    assert breadth is None

    freshness = provider.get_freshness_info()
    assert "market_breadth" in freshness
    info = freshness["market_breadth"]
    assert info.is_stale is True
    assert info.error is not None
    assert "Eastmoney" in info.error or "unreachable" in info.error


def test_a_stock_provider_empty_turnover_returns_none() -> None:
    """When the API returns empty or zero turnover, breadth is None."""
    provider = AStockLowAbsorbProvider(symbols=["601138"])

    def fake_json(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        if "clist" in url:
            return {"data": {"total": 0, "diff": []}}
        return {"data": {"diff": []}}

    provider._get_json = fake_json  # type: ignore[method-assign]

    breadth = provider.get_market_breadth(date(2026, 6, 12), SCAN_AT)
    assert breadth is None
    assert provider.provider_status["market_breadth"]["ok"] is False


# ──────────────────────────────────────────────────────────────────────────────
# Task 2: Global market provider failure and sentiment tests
# ──────────────────────────────────────────────────────────────────────────────


def test_global_market_provider_stooq_failure_records_error() -> None:
    """When Stooq HTTP fails, global provider records error and returns empty bars."""

    def failing_get(url: str, params: dict[str, object] | None = None):
        raise ConnectionError("Stooq unreachable")

    provider = GlobalMarketDataProvider(provider="stooq", http_get=failing_get)

    rows = provider.get_daily_bars(["NVDA"], date(2026, 6, 12), lookback=5)

    assert rows["NVDA"] == []
    assert provider.provider_status["daily_bars"]["ok"] is False
    assert "Stooq" in str(provider.provider_status["daily_bars"]["message"]) or "unreachable" in str(provider.provider_status["daily_bars"]["message"])

    freshness = provider.get_freshness_info()
    assert "daily_bars" in freshness
    assert freshness["daily_bars"].is_stale is True
    assert freshness["daily_bars"].error is not None


def test_global_data_abnormality_leads_to_sentiment_intercept_or_observe() -> None:
    """When global data is missing/stale, sentiment结论 must not be '允许'."""
    from src.low_absorb.sentiment import build_sentiment_permission_snapshot

    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=None,
        global_risk_error="Stooq unreachable",
    )

    permission = snapshot.get("tradingPermission", {})
    status = str(permission.get("status", ""))
    assert "允许" not in status, f"Global data missing should not yield 允许, got: {status}"
    assert "拦截" in status or "观察" in status


def test_sentiment_snapshot_with_valid_global_data() -> None:
    """When global data is healthy, sentiment includes global risk gauge."""
    from src.low_absorb.sentiment import build_sentiment_permission_snapshot

    snapshot = build_sentiment_permission_snapshot(
        global_risk_appetite=Decimal("65"),
        global_risk_error=None,
    )

    gauges = snapshot.get("gauges", [])
    global_gauges = [g for g in gauges if g.get("id") == "global"]
    assert len(global_gauges) == 1
    assert global_gauges[0]["score"] == 65
