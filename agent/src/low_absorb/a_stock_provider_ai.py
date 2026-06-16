"""AI-chain aware A-share provider adapter."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .a_stock_provider import AStockLowAbsorbProvider as BaseAStockLowAbsorbProvider
from .ai_chain_universe import (
    default_ai_chain_mainboard_universe,
    default_ai_chain_sector_symbols,
    default_symbol_industries,
    default_symbol_names,
)
from .data_provider import ChainBranchStrength, RateLimitedHttpClient


class AStockLowAbsorbProvider(BaseAStockLowAbsorbProvider):
    """A-share provider with a wider AI-chain mainboard universe.

    The base provider already implements public market data endpoints.  This
    adapter replaces the single-symbol default with a mapped AI-chain universe
    and derives branch strength from the mapped daily bars.
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
        super().__init__(
            symbols=symbols or default_ai_chain_mainboard_universe(),
            http_client=http_client,
            symbol_industries=default_symbol_industries() | (symbol_industries or {}),
            symbol_names=default_symbol_names() | (symbol_names or {}),
            max_data_staleness=max_data_staleness,
        )

    def get_chain_branch_strength(self, trade_date: date, lookback: int) -> list[ChainBranchStrength]:
        sector_symbols = default_ai_chain_sector_symbols()
        symbols = sorted({symbol for rows in sector_symbols.values() for symbol in rows})
        bars_by_symbol = self.get_daily_bars(symbols, trade_date, lookback)

        sector_returns: list[tuple[str, Decimal]] = []
        all_returns: list[Decimal] = []
        for sector, sector_list in sector_symbols.items():
            returns: list[Decimal] = []
            for symbol in sector_list:
                bars = bars_by_symbol.get(symbol, [])
                if len(bars) < 2 or bars[0].close <= 0:
                    continue
                stock_return = (bars[-1].close - bars[0].close) / bars[0].close
                returns.append(stock_return)
                all_returns.append(stock_return)
            if returns:
                sector_returns.append((sector, sum(returns, Decimal("0")) / Decimal(str(len(returns)))))

        if not sector_returns:
            self._mark_status("chain_strength", ok=False, data_source="eastmoney_kline", message="AI chain mapped daily bars unavailable")
            return []

        market_avg = sum(all_returns, Decimal("0")) / Decimal(str(len(all_returns))) if all_returns else Decimal("0")
        ranked = sorted(sector_returns, key=lambda item: item[1], reverse=True)
        total = len(ranked)
        rows: list[ChainBranchStrength] = []
        for rank, (sector, avg_return) in enumerate(ranked, start=1):
            relative_strength = Decimal("1") + (avg_return - market_avg)
            if relative_strength < Decimal("0"):
                relative_strength = Decimal("0")
            rows.append(
                ChainBranchStrength(
                    branch_name=sector,
                    rank=rank,
                    total_branches=total,
                    slope=avg_return.quantize(Decimal("0.0001")),
                    relative_strength=relative_strength.quantize(Decimal("0.0001")),
                )
            )
        self._mark_status("chain_strength", ok=True, data_source="eastmoney_kline_mapped_ai_chain", staleness_seconds=0, market_date=trade_date)
        return rows
