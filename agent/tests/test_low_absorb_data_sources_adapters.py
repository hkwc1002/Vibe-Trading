"""Tests for A-share multi-source adapter layer."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from src.low_absorb.data_sources.a_share_adapters import (
    AdapterResult,
    BaiduSinaAdapter,
    EastmoneyAdapter,
    MootdxAdapter,
    TencentAdapter,
)


class TestTencentAdapter:
    def test_fetch_quote_success(self) -> None:
        def mock_get(url: str, params: dict) -> str:
            return 'v_sh601138="1~工业富联~601138~20.50~20.00~20.55~19.80~~~~";\n'

        adapter = TencentAdapter(http_get=mock_get)
        result = adapter.fetch_quote("601138")
        assert result.ok is True
        assert result.selected_source == "tencent"
        assert result.returned_rows == 1

    def test_fetch_quote_failure(self) -> None:
        def mock_get(url: str, params: dict) -> str:
            raise ConnectionError("Tencent unavailable")

        adapter = TencentAdapter(http_get=mock_get)
        result = adapter.fetch_quote("601138")
        assert result.ok is False

    def test_source_id(self) -> None:
        adapter = TencentAdapter()
        assert adapter.source_id == "tencent"


class TestEastmoneyAdapter:
    def test_fetch_sector_success(self) -> None:
        def mock_get(url: str, params: dict) -> dict:
            return {"data": {"diff": [{"f3": 1.5, "f12": "BK1234", "f14": "AI服务器"}]}}

        adapter = EastmoneyAdapter(http_get=mock_get)
        result = adapter.fetch_sector_data()
        assert result.ok is True
        assert result.selected_source == "eastmoney"

    def test_fetch_sector_empty(self) -> None:
        def mock_get(url: str, params: dict) -> dict:
            return {"data": {"diff": []}}

        adapter = EastmoneyAdapter(http_get=mock_get)
        result = adapter.fetch_sector_data()
        assert result.ok is True
        assert result.returned_rows == 0

    def test_fetch_sector_failure(self) -> None:
        def mock_get(url: str, params: dict) -> dict:
            raise ConnectionError("Eastmoney unavailable")

        adapter = EastmoneyAdapter(http_get=mock_get)
        result = adapter.fetch_sector_data()
        assert result.ok is False

    def test_source_id(self) -> None:
        adapter = EastmoneyAdapter()
        assert "eastmoney" in adapter.source_id


class TestMootdxAdapter:
    def test_source_id(self) -> None:
        adapter = MootdxAdapter()
        assert adapter.source_id == "mootdx"

    def test_fetch_kline_mocked_failure(self) -> None:
        def mock_quotes() -> object:
            raise ConnectionError("mootdx TCP unavailable")

        adapter = MootdxAdapter(quotes_factory=mock_quotes)
        result = adapter.fetch_kline("601138", lookback=20)
        assert result.ok is False
        assert result.error_message is not None

    def test_fetch_kline_mocked_success(self) -> None:
        import pandas as pd

        class MockQuotes:
            def bars(self, symbol: int, frequency: int = 9, offset: int = 0, start: int = 0, count: int = 20):
                return pd.DataFrame({
                    "date": ["2026-06-01", "2026-06-02"],
                    "open": [20.0, 20.5],
                    "high": [20.4, 20.8],
                    "low": [19.8, 20.2],
                    "close": [20.2, 20.6],
                    "volume": [1000000, 1200000],
                    "amount": [20000000, 25000000],
                })

        adapter = MootdxAdapter(quotes_factory=lambda: MockQuotes())
        result = adapter.fetch_kline("601138", lookback=20)
        assert result.ok is True
        assert result.selected_source == "mootdx"
        assert result.returned_rows == 2


class TestBaiduSinaAdapter:
    def test_source_id(self) -> None:
        adapter = BaiduSinaAdapter()
        assert adapter.source_id == "baidu_sina"

    def test_fetch_kline_success(self) -> None:
        csv_text = "date,open,high,low,close\n2026-06-10,20.0,20.4,19.8,20.1\n2026-06-11,20.1,20.5,19.9,20.2\n2026-06-12,20.2,20.6,20.0,20.3"

        def mock_get(url: str, params: dict) -> str:
            return csv_text

        adapter = BaiduSinaAdapter(http_get=mock_get)
        result = adapter.fetch_kline("601138", lookback=2)
        assert result.ok is True
        assert result.selected_source == "baidu_sina"

    def test_fetch_kline_failure(self) -> None:
        def mock_get(url: str, params: dict) -> str:
            raise ConnectionError("Baidu/Sina unavailable")

        adapter = BaiduSinaAdapter(http_get=mock_get)
        result = adapter.fetch_kline("601138", lookback=20)
        assert result.ok is False
