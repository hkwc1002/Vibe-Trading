"""Daily-level backtest engine — runs scanner strategy over historical data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Sequence
from uuid import uuid4

from ..config import LowAbsorbConfig
from ..models import BacktestResult, BacktestRun, BacktestRunRequest
from .dataset import BACKTEST_LOOKBACK, BacktestDataset
from .metrics import BacktestMetricsCalculator
from .models import BacktestSampleRow

if TYPE_CHECKING:
    from ..data_provider import DailyBar, MarketDataProvider
    from ..storage import LowAbsorbRepository


@dataclass(frozen=True)
class BacktestScannerContext:
    """Configuration context for scanner evaluation during backtest."""

    symbols: Sequence[str]
    config: LowAbsorbConfig
    lookback: int = 20


def _make_run_id() -> str:
    return f"bt-{datetime.now():%Y%m%d%H%M%S}-{uuid4().hex[:16]}"


class BacktestEngine:
    """Runs a daily-level backtest by replaying the scanner signal funnel
    over historical daily bar data.

    This is a research analysis tool. It never creates broker orders,
    execution requests, or real trading records.
    """

    def __init__(
        self,
        config: LowAbsorbConfig,
        data_provider: MarketDataProvider,
        storage: LowAbsorbRepository,
    ) -> None:
        self._config = config
        self._provider = data_provider
        self._storage = storage
        self._dataset = BacktestDataset(data_provider, config)
        self._metrics = BacktestMetricsCalculator()

    def run(self, request: BacktestRunRequest) -> BacktestResult:
        """Execute a backtest run, persist the result, and return it."""
        result = self._execute(request)

        # Always persist the run and full result to storage
        backtest_run = BacktestRun(
            run_id=result.run_id,
            request=request,
            status=result.status,
            error=result.error,
            finished_at=datetime.now(),
        )
        self._storage.add_backtest_run(backtest_run, result=result)

        return result

    def _execute(self, request: BacktestRunRequest) -> BacktestResult:
        """Execute backtest logic without storage side effects."""
        # Fail-closed: symbols=None means no known universe
        if request.symbols is None:
            return BacktestResult(
                run_id=_make_run_id(),
                status="FAILED",
                data_sources=[],
                error="symbols 为 None：无受控股票池，无法运行回测。必须显式指定 symbols。",
                limitations=["回测未运行：缺少股票池参数。"],
            )

        if not request.symbols:
            return BacktestResult(
                run_id=_make_run_id(),
                status="SUCCEEDED",
                data_sources=["none"],
                limitations=["回测请求包含空股票池，未生成任何样本。"],
            )

        # Load historical data
        bars_by_symbol = self._dataset.load_historical_bars(
            start_date=request.start_date,
            end_date=request.end_date,
            symbols=request.symbols,
        )

        if not any(bars_by_symbol.values()):
            return BacktestResult(
                run_id=_make_run_id(),
                status="FAILED",
                data_sources=["none"],
                error=f"历史数据缺失：在 {request.start_date} 至 {request.end_date} 范围内未找到任何日线数据。",
                limitations=["回测因历史数据缺失而失败。"],
            )

        # Collect all unique trade dates sorted
        all_dates: set[date] = set()
        for symbol_bars in bars_by_symbol.values():
            for bar in symbol_bars:
                all_dates.add(bar.trade_date)

        sorted_dates = sorted(all_dates)
        if not sorted_dates:
            return BacktestResult(
                run_id=_make_run_id(),
                status="FAILED",
                data_sources=["none"],
                error="历史数据日期列表为空。",
                limitations=["回测因数据异常而失败。"],
            )

        # Build date → bars lookup
        bars_by_date: dict[date, dict[str, DailyBar]] = {}
        for td in sorted_dates:
            date_bars: dict[str, DailyBar] = {}
            for symbol, symbol_bars in bars_by_symbol.items():
                matching = [b for b in symbol_bars if b.trade_date == td]
                if matching:
                    date_bars[symbol] = matching[-1]
            if date_bars:
                bars_by_date[td] = date_bars

        # Iterate each date, evaluate candidates
        samples: list[BacktestSampleRow] = []
        signal_count = 0
        plan_count = 0
        data_sources: set[str] = set()

        for i, td in enumerate(sorted_dates):
            if td < request.start_date or td > request.end_date:
                continue

            if td not in bars_by_date:
                continue

            current_bars = bars_by_date[td]
            data_sources.add("fixture")

            # Find next trading day for forward measurement
            forward_date: date | None = None
            for fd in sorted_dates:
                if fd > td and fd in bars_by_date:
                    forward_date = fd
                    break

            if forward_date is None or forward_date not in bars_by_date:
                continue

            for symbol in request.symbols:
                if symbol not in current_bars:
                    continue

                lookback_bars = bars_by_symbol.get(symbol, [])
                eval_bars = [b for b in lookback_bars if b.trade_date <= td]

                if len(eval_bars) < BACKTEST_LOOKBACK:
                    continue

                current_bar = current_bars[symbol]
                forward_bar = bars_by_date[forward_date].get(symbol)
                if forward_bar is None:
                    continue

                signal, should_sample = self._evaluate_for_backtest(
                    symbol=symbol,
                    bars=eval_bars,
                    trade_date=td,
                )

                if signal is None:
                    continue

                signal_count += 1

                if not should_sample:
                    continue

                plan_count += 1

                sample = self._measure_outcome(
                    trade_date=td,
                    symbol=symbol,
                    current_bar=current_bar,
                    forward_bar=forward_bar,
                    branch=signal.get("branch", "未分类"),
                )
                if sample is not None:
                    samples.append(sample)

        base_data_sources = list(data_sources) if data_sources else ["fixture"]
        # Pre-compute preliminary avg_r for sensitivity generation
        pre_avg_r: Decimal = Decimal("0")
        if samples:
            pre_avg_r = sum(s.r_multiple for s in samples) / Decimal(str(len(samples)))
        computed = self._metrics.compute(samples, base_avg_r=pre_avg_r)
        limitations = self._metrics.get_limitations(
            data_sources=base_data_sources,
            has_manual_fill_assumption=request.include_manual_fill_assumption,
        )

        result = self._metrics.to_result(
            run_id=_make_run_id(),
            data_sources=base_data_sources,
            metrics=computed,
            limitations=limitations,
            signal_count=signal_count,
            plan_count=plan_count,
        )

        return result

    def _evaluate_for_backtest(
        self,
        symbol: str,
        bars: list[DailyBar],
        trade_date: date,
    ) -> tuple[dict | None, bool]:
        """Simplified signal evaluation for backtest context.

        Returns (signal_info or None, should_sample).
        """
        if len(bars) < 2:
            return None, False

        latest = bars[-1]
        recent = bars[-BACKTEST_LOOKBACK:]
        if len(recent) < BACKTEST_LOOKBACK:
            return None, False

        ma20 = sum(b.close for b in recent) / len(recent)
        if ma20 <= 0:
            return None, False

        deviation = (latest.close - ma20) / ma20

        if deviation < self._config.ma20_deviation_min or deviation > self._config.ma20_deviation_max:
            return None, False

        previous_volumes = [b.volume for b in bars[-6:-1]]
        if len(previous_volumes) < 5:
            return None, False
        avg_volume_5d = sum(previous_volumes) / len(previous_volumes)
        if avg_volume_5d <= 0:
            return None, False
        volume_ratio = latest.volume / avg_volume_5d
        if volume_ratio > self._config.max_volume_ratio_5d:
            return None, False

        if latest.atr <= 0:
            return None, False
        lower_shadow = (min(latest.open, latest.close) - latest.low) / latest.atr
        if lower_shadow < self._config.min_lower_shadow_atr:
            return None, False

        return {"branch": latest.industry, "deviation": deviation}, True

    def _measure_outcome(
        self,
        trade_date: date,
        symbol: str,
        current_bar: DailyBar,
        forward_bar: DailyBar,
        branch: str,
    ) -> BacktestSampleRow | None:
        """Measure outcome of a signal using next-day price.

        Simplified:
        - Entry at current close
        - Stop at current low
        - Exit at next day's close
        """
        entry_price = current_bar.close
        stop_loss = current_bar.low

        if entry_price <= stop_loss:
            return None

        risk = entry_price - stop_loss
        if risk <= 0:
            return None

        exit_price = forward_bar.close
        r_multiple = (exit_price - entry_price) / risk

        return BacktestSampleRow(
            trade_date=trade_date,
            symbol=symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            r_multiple=r_multiple,
            branch=branch,
            hit_stop=forward_bar.low <= stop_loss,
        )
