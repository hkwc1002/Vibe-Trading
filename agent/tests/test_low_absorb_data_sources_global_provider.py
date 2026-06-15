"""Tests for global quality provider fixes (CR-4)."""

from __future__ import annotations

from datetime import date, timedelta

from src.low_absorb.data_sources.global_provider import GlobalQualityProvider


class TestGlobalProviderFallback:
    """CR-4: Fix fallback_used field name and Stooq lookback."""

    def test_yfinance_failure_stooq_fallback_marks_fallback_used(self) -> None:
        def fail_yfinance(symbol: str) -> object:
            raise ConnectionError("yfinance down")

        def mock_stooq(url: str, params: dict) -> str:
            return "Date,Open,High,Low,Close,Volume\n2026-06-10,100,101,99,100.5,100000\n2026-06-11,101,102,100,101.5,120000\n2026-06-12,101.5,103,101,102,110000\n2026-06-13,102,104,101.5,103.5,130000\n2026-06-14,103.5,105,103,104,125000"

        provider = GlobalQualityProvider(provider="auto", ticker_factory=fail_yfinance, http_get=mock_stooq)
        results = provider.fetch_daily_bars(symbols=["NVDA"], end=date(2026, 6, 14), lookback=5)
        nvda = results["NVDA"]
        assert nvda.ok is True
        assert nvda.selected_source == "stooq"
        assert nvda.fallback_used is True, "fallback_used should be True when yfinance fails and Stooq succeeds"

    def test_stooq_lookback_returns_multiple_days(self) -> None:
        def mock_stooq(url: str, params: dict) -> str:
            d1 = params.get("d1", "")
            d2 = params.get("d2", "")
            assert d1 < d2, "d1 should be before d2 for multi-day lookback"
            return "Date,Open,High,Low,Close,Volume\n2026-06-10,100,101,99,100.5,100000\n2026-06-11,101,102,100,101.5,120000\n2026-06-12,101.5,103,101,102,110000\n2026-06-13,102,104,101.5,103.5,130000\n2026-06-14,103.5,105,103,104,125000"

        provider = GlobalQualityProvider(provider="stooq", http_get=mock_stooq)
        results = provider.fetch_daily_bars(symbols=["NVDA"], end=date(2026, 6, 14), lookback=20)
        assert results["NVDA"].ok is True

    def test_yfinance_success_no_stooq_fallback(self) -> None:
        def success_yfinance(symbol: str) -> object:
            import pandas as pd
            class FakeTicker:
                def history(self, period, interval):
                    dates = pd.date_range(end="2026-06-14", periods=5, freq="D")
                    return pd.DataFrame({
                        "Open": [100, 101, 102, 103, 104],
                        "High": [101, 102, 103, 104, 105],
                        "Low": [99, 100, 101, 102, 103],
                        "Close": [100.5, 101.5, 102.5, 103.5, 104.5],
                        "Volume": [100000] * 5,
                    }, index=dates)
            return FakeTicker()

        provider = GlobalQualityProvider(provider="auto", ticker_factory=success_yfinance)
        results = provider.fetch_daily_bars(symbols=["NVDA"], end=date(2026, 6, 14), lookback=5)
        assert results["NVDA"].ok is True
        assert results["NVDA"].selected_source == "yfinance"
        assert results["NVDA"].fallback_used is False
