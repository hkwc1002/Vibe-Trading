from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from src.low_absorb.models import ManualPosition, PositionStatus
from src.low_absorb.risk import calculate_position_risk


def test_calculate_position_risk_for_active_manual_position() -> None:
    position = ManualPosition(
        position_id="pos-601138-20260612",
        plan_id="plan-601138-20260612",
        stock_code="601138",
        stock_name="工业富联",
        opened_at=datetime(2026, 6, 12, 14, 55),
        cost_price=Decimal("18.78"),
        current_price=Decimal("18.92"),
        stop_loss=Decimal("17.88"),
        quantity=1000,
        position_pct=Decimal("0.12"),
        status=PositionStatus.ACTIVE_POSITION,
    )

    risk = calculate_position_risk(position)

    assert risk.initial_risk_amount == Decimal("900.00")
    assert risk.current_risk_amount == Decimal("1040.00")
    assert risk.r_multiple == Decimal("0.16")
    assert risk.risk_level == "watch"
    assert risk.needs_supervision is True


def test_calculate_position_risk_marks_stop_break_as_danger() -> None:
    position = ManualPosition(
        position_id="pos-601138-20260612",
        plan_id="plan-601138-20260612",
        stock_code="601138",
        stock_name="工业富联",
        opened_at=datetime(2026, 6, 12, 14, 55),
        cost_price=Decimal("18.78"),
        current_price=Decimal("17.80"),
        stop_loss=Decimal("17.88"),
        quantity=1000,
        position_pct=Decimal("0.12"),
        status=PositionStatus.HOLDING_REVIEW,
    )

    risk = calculate_position_risk(position)

    assert risk.current_risk_amount == Decimal("0.00")
    assert risk.r_multiple == Decimal("-1.09")
    assert risk.risk_level == "danger"
    assert risk.needs_supervision is True


def test_calculate_position_risk_rejects_non_positive_initial_risk() -> None:
    position = ManualPosition(
        position_id="pos-601138-20260612",
        plan_id="plan-601138-20260612",
        stock_code="601138",
        stock_name="工业富联",
        opened_at=datetime(2026, 6, 12, 14, 55),
        cost_price=Decimal("18.78"),
        current_price=Decimal("18.92"),
        stop_loss=Decimal("18.78"),
        quantity=1000,
        position_pct=Decimal("0.12"),
        status=PositionStatus.ACTIVE_POSITION,
    )

    with pytest.raises(ValueError, match="initial risk"):
        calculate_position_risk(position)
