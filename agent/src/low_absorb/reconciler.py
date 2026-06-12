"""Manual fill reconciliation helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from .models import ManualFill, ManualPosition, ManualTradePlan, PositionStatus
from .storage import InMemoryLowAbsorbStorage

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class ManualFillReconciler:
    """Apply user-recorded manual fills to the manual position book."""

    def __init__(self, storage: InMemoryLowAbsorbStorage) -> None:
        self.storage = storage

    def record_fill(self, fill: ManualFill) -> ManualPosition:
        self.storage.fills[fill.fill_id] = fill
        if fill.side == "BUY":
            return self._record_buy(fill)
        return self._record_sell(fill)

    def _record_buy(self, fill: ManualFill) -> ManualPosition:
        existing = self._find_open_position(fill.stock_code)
        plan = self.storage.trade_plans.get(fill.plan_id or "")
        if existing is None:
            position = ManualPosition(
                position_id=f"pos-{fill.stock_code}-{fill.plan_id or fill.fill_id}",
                plan_id=fill.plan_id,
                stock_code=fill.stock_code,
                stock_name=fill.stock_name,
                opened_at=fill.executed_at or fill.filled_at,
                avg_cost=fill.actual_price,
                current_price=fill.actual_price,
                initial_stop_price=plan.stop_loss if plan else fill.actual_price,
                current_stop_price=plan.stop_loss if plan else fill.actual_price,
                quantity=fill.quantity,
                position_weight=plan.planned_position_pct if plan else None,
                status=PositionStatus.ACTIVE_POSITION,
                notes=[item for item in [fill.execution_note, fill.subjective_reason, fill.note] if item],
            )
        else:
            old_value = (existing.avg_cost or existing.cost_price or Decimal("0")) * existing.quantity
            added_value = (fill.actual_price or Decimal("0")) * fill.quantity
            new_quantity = existing.quantity + fill.quantity
            position = existing.model_copy(
                update={
                    "quantity": new_quantity,
                    "avg_cost": _money((old_value + added_value) / Decimal(new_quantity)),
                    "cost_price": _money((old_value + added_value) / Decimal(new_quantity)),
                    "current_price": fill.actual_price,
                    "status": PositionStatus.ACTIVE_POSITION,
                    "notes": [*existing.notes, *[item for item in [fill.execution_note, fill.subjective_reason] if item]],
                }
            )
        self.storage.positions[position.position_id] = position
        return position

    def _record_sell(self, fill: ManualFill) -> ManualPosition:
        existing = self._find_open_position(fill.stock_code)
        if existing is None:
            raise ValueError("no active position for sell fill")
        if fill.quantity > existing.quantity:
            raise ValueError("sell quantity exceeds active position")
        remaining = existing.quantity - fill.quantity
        update = {
            "quantity": remaining,
            "current_price": fill.actual_price,
            "notes": [*existing.notes, *[item for item in [fill.execution_note, fill.subjective_reason] if item]],
        }
        if remaining == 0:
            update["status"] = PositionStatus.CLOSED
            update["closed_at"] = fill.executed_at or fill.filled_at or datetime.now()
        position = existing.model_copy(update=update)
        self.storage.positions[position.position_id] = position
        return position

    def _find_open_position(self, stock_code: str) -> ManualPosition | None:
        for position in self.storage.positions.values():
            if position.stock_code == stock_code and position.status not in {
                PositionStatus.CLOSED,
                PositionStatus.MANUAL_EXITED,
                PositionStatus.INVALIDATED,
            }:
                return position
        return None


def reconcile_manual_fill(plan: ManualTradePlan, fill: ManualFill) -> ManualPosition:
    """Convert a user-recorded manual fill into a supervised manual position."""

    return ManualPosition(
        position_id=f"pos-{fill.stock_code}-{fill.filled_at:%Y%m%d%H%M%S}",
        plan_id=plan.plan_id,
        stock_code=fill.stock_code,
        stock_name=fill.stock_name,
        opened_at=fill.filled_at,
        avg_cost=fill.actual_price,
        current_price=fill.actual_price,
        initial_stop_price=plan.stop_loss,
        current_stop_price=plan.stop_loss,
        quantity=fill.quantity,
        position_weight=plan.planned_position_pct,
        status=PositionStatus.ACTIVE_POSITION,
        note=fill.note,
    )
