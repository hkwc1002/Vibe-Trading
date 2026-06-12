"""R-risk calculation for manual Low Absorb positions."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import ManualPosition, PositionRisk, PositionStatus

CENT = Decimal("0.01")
STANDARD_LOT_SHARES = Decimal("100")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _r_value(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_open_stop_risk_cny(
    *,
    entry_price: Decimal,
    stop_loss: Decimal,
    shares: Decimal = STANDARD_LOT_SHARES,
) -> Decimal:
    """Calculate manual plan stop risk in CNY for a reference share size."""

    if entry_price <= stop_loss:
        raise ValueError("entry_price must be greater than stop_loss")
    if shares <= 0:
        raise ValueError("shares must be positive")
    return _money((entry_price - stop_loss) * shares)


def calculate_position_risk(position: ManualPosition) -> PositionRisk:
    """Calculate initial risk, current risk, and R multiple for a manual position."""

    avg_cost = position.avg_cost or position.cost_price
    initial_stop = position.initial_stop_price or position.stop_loss
    current_stop = position.current_stop_price or position.stop_loss or initial_stop
    if avg_cost is None or initial_stop is None or current_stop is None:
        raise ValueError("position cost and stop prices are required")

    initial_risk_per_share = avg_cost - initial_stop
    if initial_risk_per_share <= 0:
        raise ValueError("initial risk must be positive")

    current_price = position.current_price
    current_risk_per_share = (
        max(current_price - current_stop, Decimal("0"))
        if current_price is not None
        else initial_risk_per_share
    )
    initial_risk_amount = _money(initial_risk_per_share * position.quantity)
    current_risk_amount = _money(current_risk_per_share * position.quantity)
    r_multiple = (
        _r_value(((current_price - avg_cost) * position.quantity) / initial_risk_amount)
        if current_price is not None and initial_risk_amount > 0
        else Decimal("0")
    )

    if current_price is not None and current_price <= current_stop:
        risk_level = "danger"
    elif r_multiple < Decimal("0"):
        risk_level = "warning"
    elif r_multiple < Decimal("0.5"):
        risk_level = "watch"
    else:
        risk_level = "normal"

    needs_supervision = risk_level in {"watch", "warning", "danger"} or position.status in {
        PositionStatus.HOLDING_REVIEW,
        PositionStatus.EXIT_SUGGESTED,
    }

    return PositionRisk(
        position_id=position.position_id,
        stock_code=position.stock_code,
        stock_name=position.stock_name,
        initial_risk_amount=initial_risk_amount,
        current_risk_amount=current_risk_amount,
        initial_risk_cny=initial_risk_amount,
        current_stop_risk_cny=current_risk_amount,
        r_multiple=r_multiple,
        max_loss_pct_of_equity=None,
        supervision_status="10:00 需监督" if needs_supervision else "正常跟踪",
        risk_level=risk_level,
        needs_supervision=needs_supervision,
    )
