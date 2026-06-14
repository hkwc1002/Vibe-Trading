from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from src.low_absorb.models import ManualFill, ManualTradePlan, PositionStatus
from src.low_absorb.reconciler import ManualFillReconciler
from src.low_absorb.risk import calculate_position_risk
from src.low_absorb.storage import InMemoryLowAbsorbStorage


def _plan() -> ManualTradePlan:
    return ManualTradePlan(
        plan_id="plan-601138-20260612",
        signal_id="sig-601138-20260612",
        trade_date=date(2026, 6, 12),
        stock_code="601138",
        stock_name="工业富联",
        entry_low=Decimal("18.60"),
        entry_high=Decimal("18.95"),
        stop_loss=Decimal("17.88"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.0035"),
        initial_risk_r=Decimal("1.0"),
        manual_order_text="601138 工业富联，人工低吸区间 18.60-18.95，参考止损 17.88。",
    )


def _fill(
    fill_id: str,
    *,
    side: str = "BUY",
    actual_price: Decimal = Decimal("18.78"),
    quantity: int = 1000,
    planned_price: Decimal | None = Decimal("18.70"),
) -> ManualFill:
    return ManualFill(
        fill_id=fill_id,
        plan_id="plan-601138-20260612",
        signal_id="sig-601138-20260612",
        stock_code="601138",
        stock_name="工业富联",
        side=side,
        planned_price=planned_price,
        actual_price=actual_price,
        quantity=quantity,
        fee=Decimal("5.00"),
        executed_at=datetime(2026, 6, 12, 14, 55),
        execution_note="用户回填人工成交。",
        subjective_reason="按系统计划人工执行。",
    )


def test_manual_buy_fill_creates_active_position_and_slippage() -> None:
    storage = InMemoryLowAbsorbStorage()
    plan = _plan()
    storage.trade_plans[plan.plan_id] = plan
    reconciler = ManualFillReconciler(storage)

    position = reconciler.record_fill(_fill("fill-buy-1"))

    assert position.status is PositionStatus.ACTIVE_POSITION
    assert position.quantity == 1000
    assert position.avg_cost == Decimal("18.78")
    assert position.initial_stop_price == Decimal("17.88")
    assert storage.fills["fill-buy-1"].slippage == Decimal("0.08")
    assert storage.positions[position.position_id] == position


def test_manual_buy_fill_updates_average_cost() -> None:
    storage = InMemoryLowAbsorbStorage()
    plan = _plan()
    storage.trade_plans[plan.plan_id] = plan
    reconciler = ManualFillReconciler(storage)

    first = reconciler.record_fill(_fill("fill-buy-1", actual_price=Decimal("18.00"), quantity=1000))
    second = reconciler.record_fill(_fill("fill-buy-2", actual_price=Decimal("19.00"), quantity=1000))

    assert first.position_id == second.position_id
    assert second.quantity == 2000
    assert second.avg_cost == Decimal("18.50")


def test_manual_sell_fill_reduces_position() -> None:
    storage = InMemoryLowAbsorbStorage()
    plan = _plan()
    storage.trade_plans[plan.plan_id] = plan
    reconciler = ManualFillReconciler(storage)
    opened = reconciler.record_fill(_fill("fill-buy-1", quantity=1000))

    reduced = reconciler.record_fill(_fill("fill-sell-1", side="SELL", actual_price=Decimal("19.10"), quantity=400))

    assert reduced.position_id == opened.position_id
    assert reduced.quantity == 600
    assert reduced.status is PositionStatus.ACTIVE_POSITION


def test_manual_sell_fill_closes_position() -> None:
    storage = InMemoryLowAbsorbStorage()
    plan = _plan()
    storage.trade_plans[plan.plan_id] = plan
    reconciler = ManualFillReconciler(storage)
    opened = reconciler.record_fill(_fill("fill-buy-1", quantity=1000))

    closed = reconciler.record_fill(_fill("fill-sell-1", side="SELL", actual_price=Decimal("19.10"), quantity=1000))

    assert closed.position_id == opened.position_id
    assert closed.quantity == 0
    assert closed.status is PositionStatus.CLOSED
    assert closed.closed_at is not None


def test_risk_recalculation_uses_initial_risk_current_stop_and_r_multiple() -> None:
    storage = InMemoryLowAbsorbStorage()
    plan = _plan()
    storage.trade_plans[plan.plan_id] = plan
    position = ManualFillReconciler(storage).record_fill(_fill("fill-buy-1", quantity=1000))
    position = position.model_copy(update={"current_price": Decimal("18.20")})

    risk = calculate_position_risk(position)

    assert risk.position_id == position.position_id
    assert risk.initial_risk_cny == Decimal("900.00")
    assert risk.current_stop_risk_cny == Decimal("320.00")
    assert risk.r_multiple == Decimal("-0.64")


def test_invalid_manual_fill_quantity_rejected() -> None:
    with pytest.raises(ValueError):
        _fill("fill-bad", quantity=0)
