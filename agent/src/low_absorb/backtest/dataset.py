"""Historical daily-bar dataset loader for backtesting."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from ..config import LowAbsorbConfig

if TYPE_CHECKING:
    from ..data_provider import DailyBar, MarketDataProvider


BACKTEST_LOOKBACK = 20
"""Default lookback window for MA20 calculation."""


class BacktestDataset:
    """Loads historical daily bars from a MarketDataProvider for backtesting."""

    def __init__(
        self,
        data_provider: MarketDataProvider,
        config: LowAbsorbConfig | None = None,
    ) -> None:
        self._provider = data_provider
        self._config = config or LowAbsorbConfig()

    def load_historical_bars(
        self,
        start_date: date,
        end_date: date,
        symbols: list[str],
    ) -> dict[str, list[DailyBar]]:
        """Load daily bars for the given symbols and date range.

        Fetches enough lookback data so that the first evaluation date
        has at least BACKTEST_LOOKBACK bars.

        Returns a dict keyed by symbol; missing symbols have empty lists.
        """
        if not symbols:
            return {}

        fetch_end = end_date
        fetch_start = start_date - timedelta(days=BACKTEST_LOOKBACK * 2)

        raw = self._provider.get_daily_bars(symbols, fetch_end, lookback=9999)

        result: dict[str, list[DailyBar]] = {}
        for symbol in symbols:
            all_bars = raw.get(symbol) or []
            result[symbol] = [
                bar
                for bar in all_bars
                if fetch_start <= bar.trade_date <= fetch_end
            ]
        return result
