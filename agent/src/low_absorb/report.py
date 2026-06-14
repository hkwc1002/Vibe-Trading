"""Close report builder for Low Absorb review workflow."""

from __future__ import annotations

from datetime import date

from .models import (
    CloseReport,
    LowAbsorbSignal,
    ManualPosition,
    ManualTradePlan,
    PositionStatus,
    SignalStatus,
    TradePlanStatus,
)


def _pending_fills_count(trade_plans: list[ManualTradePlan]) -> int:
    """Count plans that have not yet been filled."""
    return sum(1 for plan in trade_plans if plan.status != TradePlanStatus.MANUAL_FILLED)


def _invalidated_signals_count(signals: list[LowAbsorbSignal]) -> int:
    """Count signals marked as invalidated."""
    return sum(1 for signal in signals if signal.status == SignalStatus.INVALIDATED)


def _active_positions_next_day(positions: list[ManualPosition]) -> list[ManualPosition]:
    """Return positions that need next-day supervision."""
    return [
        p
        for p in positions
        if p.status in {PositionStatus.ACTIVE_POSITION, PositionStatus.HOLDING_REVIEW}
    ]


def _build_review_items(
    existing: list[str] | None,
    pending_fills: int,
    invalidated_signals: int,
    active_positions: list[ManualPosition],
) -> list[str]:
    """Combine manually provided review items with computed supervision items."""
    items: list[str] = list(existing) if existing else []
    if pending_fills > 0:
        items.append(f"待人工成交回填：{pending_fills} 笔")
    if invalidated_signals > 0:
        items.append(f"今日失效候选信号：{invalidated_signals} 个")
    if active_positions:
        items.append(f"次日 10:00 需要监督的持仓：{len(active_positions)} 个")
    return items


def build_close_report(
    *,
    report_id: str,
    trade_date: date,
    signals: list[LowAbsorbSignal],
    trade_plans: list[ManualTradePlan],
    positions: list[ManualPosition],
    review_items: list[str] | None = None,
) -> CloseReport:
    """Build a close report from manual workflow state.

    The report includes computed supervision items appended to any
    caller-provided *review_items*.
    """
    pending_fills = _pending_fills_count(trade_plans)
    invalidated_signals = _invalidated_signals_count(signals)
    active_positions = _active_positions_next_day(positions)

    combined = _build_review_items(
        existing=review_items,
        pending_fills=pending_fills,
        invalidated_signals=invalidated_signals,
        active_positions=active_positions,
    )

    return CloseReport(
        report_id=report_id,
        trade_date=trade_date,
        summary=f"{trade_date:%Y-%m-%d} AI Low Absorb 收盘复盘",
        signals=signals,
        trade_plans=trade_plans,
        positions=positions,
        review_items=combined,
    )
