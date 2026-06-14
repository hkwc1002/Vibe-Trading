"""Manual trade-plan creation helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .models import LowAbsorbSignal, ManualTradePlan, TradePlanStatus


def create_manual_trade_plan(
    *,
    signal: LowAbsorbSignal,
    trade_date: date,
    entry_low: Decimal,
    entry_high: Decimal,
    stop_loss: Decimal,
    planned_position_pct: Decimal,
    max_risk_pct: Decimal,
    initial_risk_r: Decimal = Decimal("1"),
    initial_risk_cny: Decimal = Decimal("0"),
    open_stop_risk_cny: Decimal = Decimal("0"),
    r_multiple: Decimal = Decimal("0"),
    rationale: str = "",
    chain_explanation: str = "",
    branch_strength: Decimal = Decimal("0"),
    cost_signal_weight: Decimal = Decimal("0"),
    priority_score: Decimal = Decimal("0"),
    downgrade_reason: str = "",
    block_reason: str = "",
    sector_role: str = "",
) -> ManualTradePlan:
    """Create a manual plan object without any execution channel."""

    manual_text = (
        f"{signal.stock_code} {signal.stock_name}，人工低吸区间 {entry_low}-{entry_high}，"
        f"参考止损 {stop_loss}，计划仓位 {planned_position_pct}。{rationale}"
    )
    return ManualTradePlan(
        plan_id=f"plan-{signal.stock_code}-{trade_date:%Y%m%d}",
        signal_id=signal.signal_id,
        trade_date=trade_date,
        stock_code=signal.stock_code,
        stock_name=signal.stock_name,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop_loss,
        planned_position_pct=planned_position_pct,
        max_risk_pct=max_risk_pct,
        initial_risk_r=initial_risk_r,
        initial_risk_cny=initial_risk_cny,
        open_stop_risk_cny=open_stop_risk_cny,
        r_multiple=r_multiple,
        rationale=rationale,
        manual_order_text=manual_text,
        status=TradePlanStatus.RECOMMENDED,
        chain_explanation=chain_explanation,
        branch_strength=branch_strength,
        cost_signal_weight=cost_signal_weight,
        priority_score=priority_score,
        downgrade_reason=downgrade_reason,
        block_reason=block_reason,
        sector_role=sector_role,
    )
