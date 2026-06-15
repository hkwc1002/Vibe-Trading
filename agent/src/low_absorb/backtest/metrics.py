"""Backtest metrics calculation — win rate, drawdown, attribution, sensitivity."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence

from ..models import (
    BacktestBranchAttribution,
    BacktestResult,
    BacktestSensitivityRow,
)
from .models import BacktestSampleRow


@dataclass(frozen=True)
class LimitationReport:
    """Standardised set of backtest limitations / disclaimers."""

    limitations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ComputedMetrics:
    """Aggregated output from metrics calculation."""

    sample_count: int = 0
    signal_count: int = 0
    plan_count: int = 0
    win_rate: Decimal = Decimal("0")
    average_r: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    branch_attribution: list[BacktestBranchAttribution] = field(default_factory=list)
    sensitivity: list[BacktestSensitivityRow] = field(default_factory=list)


class BacktestMetricsCalculator:
    """Computes win rate, average R, max drawdown, branch attribution,
    and sensitivity analysis from a sequence of sample rows."""

    def compute(
        self,
        samples: Sequence[BacktestSampleRow],
        base_win_rate: Decimal | None = None,
        base_avg_r: Decimal | None = None,
    ) -> ComputedMetrics:
        """Compute aggregate metrics from backtest samples."""
        sample_count = len(samples)

        if sample_count == 0:
            return ComputedMetrics()

        winners = sum(1 for s in samples if s.r_multiple > 0)
        win_rate = Decimal(str(winners)) / Decimal(str(sample_count))
        total_r = sum(s.r_multiple for s in samples)
        average_r = total_r / Decimal(str(sample_count))

        # Max drawdown: cumulative P&L in R multiples
        cumulative = Decimal("0")
        max_dd = Decimal("0")
        for s in samples:
            cumulative += s.r_multiple
            if cumulative < max_dd:
                max_dd = cumulative

        # Branch attribution
        branch_samples: dict[str, list[Decimal]] = defaultdict(list)
        for s in samples:
            branch_samples[s.branch].append(s.r_multiple)

        total_abs_r = sum(abs(s.r_multiple) for s in samples) or Decimal("1")
        attribution: list[BacktestBranchAttribution] = []
        for branch, r_values in sorted(branch_samples.items()):
            count = len(r_values)
            branch_avg_r = sum(r_values) / Decimal(str(count))
            branch_abs_r = sum(abs(v) for v in r_values)
            contribution = branch_abs_r / total_abs_r
            attribution.append(BacktestBranchAttribution(
                branch=branch,
                sample_count=count,
                average_r=branch_avg_r,
                contribution_pct=min(contribution, Decimal("1")),
            ))
        attribution.sort(key=lambda a: a.contribution_pct, reverse=True)

        # Sensitivity (simple parameter shift approximation)
        sensitivity: list[BacktestSensitivityRow] = []
        if base_avg_r is not None and base_avg_r != 0:
            tight_win_rate = min(win_rate * Decimal("1.2"), Decimal("1"))
            relaxed_win_rate = max(win_rate * Decimal("0.8"), Decimal("0"))
            sensitivity = [
                BacktestSensitivityRow(
                    parameter="信号筛选宽松度",
                    base=win_rate,
                    variant=relaxed_win_rate,
                    description="宽松筛选假设下的理论胜率",
                ),
                BacktestSensitivityRow(
                    parameter="信号筛选严格度",
                    base=win_rate,
                    variant=tight_win_rate,
                    description="严格筛选假设下的理论胜率",
                ),
            ]

        return ComputedMetrics(
            sample_count=sample_count,
            win_rate=win_rate,
            average_r=average_r,
            max_drawdown=max_dd,
            branch_attribution=attribution,
            sensitivity=sensitivity,
        )

    def get_limitations(
        self,
        data_sources: list[str],
        has_manual_fill_assumption: bool = False,
    ) -> LimitationReport:
        """Return a standard set of backtest limitations."""
        limitations: list[str] = [
            "回测基于日线级历史数据，不模拟真实盘中成交和滑点影响。",
            "回测结果基于固定策略参数和历史市场条件，不能保证未来表现。",
            "本回测结果仅为策略研究参考，不构成投资建议和收益承诺。",
            "信号生成和交易计划基于 Tail-session 扫描漏斗，与真实盘中的决策可能存在偏差。",
        ]
        if "fixture" in data_sources:
            limitations.append("使用 fixture/模拟数据运行；非真实历史行情。")
        if has_manual_fill_assumption:
            limitations.append("包含人工成交假设，实际成交价格可能与假设存在偏差。")
        return LimitationReport(limitations=limitations)

    def to_result(
        self,
        run_id: str,
        data_sources: list[str],
        metrics: ComputedMetrics,
        limitations: LimitationReport,
        signal_count: int = 0,
        plan_count: int = 0,
    ) -> BacktestResult:
        """Build a full BacktestResult from computed metrics."""
        return BacktestResult(
            run_id=run_id,
            status="SUCCEEDED",
            data_sources=data_sources,
            sample_count=metrics.sample_count,
            signal_count=signal_count,
            plan_count=plan_count,
            win_rate=metrics.win_rate,
            average_r=metrics.average_r,
            max_drawdown=metrics.max_drawdown,
            branch_attribution=metrics.branch_attribution,
            sensitivity=metrics.sensitivity,
            limitations=limitations.limitations,
        )
