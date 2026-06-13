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
    assert body["data_source"] == "provider"


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
