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
    def test_fetch_quote_sh_prefix(self) -> None:
        urls: list[str] = []
        def mock_get(url: str, params: dict) -> str:
            urls.append(url)
            return 'v_sh601138="1~IFL~601138~20.50~20.00~20.55~19.80~~~~";\n'
        adapter = TencentAdapter(http_get=mock_get)
        result = adapter.fetch_quote("601138")
        assert result.ok
        assert "sh601138" in urls[0]
        assert isinstance(result.data, dict)
        assert result.data.get("price") == 20.50
        assert result.data.get("close") == 20.00
        assert result.data.get("open") == 20.55

    def test_fetch_quote_sz_prefix(self) -> None:
        urls: list[str] = []
        def mock_get(url: str, params: dict) -> str:
            urls.append(url)
            return 'v_sz000001="1~PAB~000001~21.50~21.00~21.60~20.90~~~~";\n'
        adapter = TencentAdapter(http_get=mock_get)
        result = adapter.fetch_quote("000001")
        assert result.ok
        assert "sz000001" in urls[0]
        assert result.data.get("code") == "000001"
        assert result.data.get("price") == 21.50

    def test_fetch_quote_failure(self) -> None:
        def mock_get(url: str, params: dict) -> str:
            raise ConnectionError("down")
        adapter = TencentAdapter(http_get=mock_get)
        result = adapter.fetch_quote("601138")
        assert not result.ok

    def test_source_id(self) -> None:
        adapter = TencentAdapter()
        assert adapter.source_id == "tencent"


class TestEastmoneyAdapter:
    def test_fetch_sector_success(self) -> None:
        def mock_get(url: str, params: dict) -> dict:
            return {"data": {"diff": [{"f3": 1.5, "f12": "BK1234", "f14": "AI"}]}}
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
            raise ConnectionError("down")
        adapter = EastmoneyAdapter(http_get=mock_get)
        result = adapter.fetch_sector_data()
        assert not result.ok

    def test_source_id(self) -> None:
        adapter = EastmoneyAdapter()
        assert "eastmoney" in adapter.source_id


class TestMootdxAdapter:
    def test_source_id(self) -> None:
        adapter = MootdxAdapter()
        assert adapter.source_id == "mootdx"

    def test_fetch_kline_failure(self) -> None:
        def mock_factory() -> object:
            raise ConnectionError("down")
        adapter = MootdxAdapter(quotes_factory=mock_factory)
        result = adapter.fetch_kline("601138", lookback=20)
        assert not result.ok

    def test_fetch_kline_success(self) -> None:
        import pandas as pd
        class MockQuotes:
            def bars(self, symbol, frequency=9, offset=0, start=0, count=20):
                return pd.DataFrame({"date": ["2026-06-01", "2026-06-02"], "open": [20.0, 20.5], "high": [20.4, 20.8], "low": [19.8, 20.2], "close": [20.2, 20.6], "volume": [1000000, 1200000], "amount": [20000000, 25000000]})
        adapter = MootdxAdapter(quotes_factory=lambda: MockQuotes())
        result = adapter.fetch_kline("601138", lookback=20)
        assert result.ok
        assert result.selected_source == "mootdx"
        assert result.returned_rows == 2


class TestBaiduSinaAdapter:
    def test_source_id(self) -> None:
        adapter = BaiduSinaAdapter()
        assert adapter.source_id == "baidu_sina"

    def test_fetch_kline_structured_output(self) -> None:
        rows = ["date,open,high,low,close,pre_close,chg,pchg,turnover,volume,amount,tcap,mcap",
                "2026-06-10,20.0,20.4,19.8,20.1,19.9,0.2,1.01,0.5,1000000,20000000,50000000000,48000000000",
                "2026-06-11,20.1,20.5,19.9,20.2,20.1,0.1,0.50,0.4,1200000,24000000,51000000000,49000000000",
                "2026-06-12,20.2,20.6,20.0,20.3,20.2,0.1,0.50,0.3,1100000,22000000,52000000000,50000000000"]
        csv_text = "\n".join(rows) + "\n"
        def mock_get(url: str, params: dict) -> str:
            return csv_text
        adapter = BaiduSinaAdapter(http_get=mock_get)
        result = adapter.fetch_kline("601138", lookback=2)
        assert result.ok
        assert result.selected_source == "baidu_sina"
        assert isinstance(result.data, list)
        if result.data:
            first = result.data[0]
            assert isinstance(first, dict)
            assert "trade_date" in first
            assert "open" in first
            assert "high" in first
            assert "low" in first
            assert "close" in first
        # Freshness from trade_date (2026-06-12 is 3 days before today 2026-06-15)
        assert result.freshness_seconds is not None
        assert result.freshness_seconds > 0, "Old K-line data should have positive freshness"

    def test_fetch_kline_old_data_is_stale(self) -> None:
        """Old trade dates should result in large freshness_seconds (stale)."""
        rows = ["date,open,high,low,close,pre_close,chg,pchg,turnover,volume,amount,tcap,mcap",
                "2026-05-01,19.0,19.5,18.8,19.2,19.0,0.2,1.05,0.5,900000,18000000,48000000000,46000000000"]
        csv_text = "\n".join(rows) + "\n"
        def mock_get(url: str, params: dict) -> str:
            return csv_text
        adapter = BaiduSinaAdapter(http_get=mock_get)
        result = adapter.fetch_kline("601138", lookback=5)
        assert result.ok
        # 2026-05-01 is 45 days before 2026-06-15, so freshness > 3600 * 24 * 44
        assert result.freshness_seconds is not None
        assert result.freshness_seconds > 3600 * 24, "Month-old data should be stale (>1 day)"

    def test_fetch_kline_failure(self) -> None:
        def mock_get(url: str, params: dict) -> str:
            raise ConnectionError("down")
        adapter = BaiduSinaAdapter(http_get=mock_get)
        result = adapter.fetch_kline("601138", lookback=20)
        assert not result.ok
