"""Position supervision helpers for the next-day risk workflow."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from .config import LowAbsorbConfig
from .data_provider import IntradayBar, MarketDataProvider
from .models import ManualPosition, MorningSupervisionResult, PositionRisk, RiskSupervisionStatus
from .risk import calculate_position_risk

ZERO = Decimal("0")


def _pct(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))


def _latest_bar(bars: list[IntradayBar]) -> IntradayBar:
    if not bars:
        raise ValueError("intraday bars are required")
    return sorted(bars, key=lambda bar: bar.at)[-1]


def supervise_position_morning(
    *,
    position: ManualPosition,
    provider: MarketDataProvider,
    trade_date: date,
    observed_at: datetime,
    config: LowAbsorbConfig | None = None,
) -> MorningSupervisionResult:
    """Classify next-day morning risk without performing any broker action."""

    config = config or LowAbsorbConfig()
    bars = provider.get_intraday_bars(position.stock_code, trade_date, "30m")
    bar = _latest_bar(bars)
    open_price = bar.open
    current_price = bar.close
    stop_price = position.current_stop_price or position.stop_loss
    if stop_price is None:
        raise ValueError("current stop price is required")

    in_noise_window = config.anti_noise_start <= observed_at.time() < config.anti_noise_end
    if in_noise_window:
        crash_trigger = open_price * (Decimal("1") + config.morning_crash_pct)
        if current_price <= crash_trigger:
            status = RiskSupervisionStatus.CRASH_WARNING
            should_notify = True
            reason = "price moved beyond morning crash threshold"
            recommendation = "manual risk review required"
        else:
            status = RiskSupervisionStatus.HOLD_NOISE
            should_notify = False
            reason = "09:30-10:00 noise window ignores ordinary weak breaks"
            recommendation = "continue scheduled 10:00 supervision"
        return MorningSupervisionResult(
            position_id=position.position_id,
            stock_code=position.stock_code,
            stock_name=position.stock_name,
            observed_at=observed_at,
            status=status,
            should_notify_feishu=should_notify,
            open_price=open_price,
            current_price=current_price,
            first_30m_close=current_price,
            reason=reason,
            recommendation=recommendation,
        )

    industry_return = provider.get_industry_return(
        position.branch or "",
        trade_date,
        config.anti_noise_start,
        config.anti_noise_end,
    )
    industry_return = industry_return if industry_return is not None else ZERO
    stock_return = (current_price / open_price) - Decimal("1")
    industry_alpha = stock_return - industry_return

    if current_price >= stop_price:
        status = RiskSupervisionStatus.HOLD_NOISE
        should_notify = False
        stop_break_pct = ZERO
        reason = "first 30m close is above current stop"
        recommendation = "continue position supervision"
    else:
        stop_break_pct = (stop_price - current_price) / stop_price
        relaxed = (
            industry_alpha >= config.alpha_relax_threshold
            and stop_break_pct <= config.max_relaxed_stop_tolerance
        )
        if relaxed:
            status = RiskSupervisionStatus.HOLD_WITH_WARNING
            should_notify = config.notify_hold_warning
            reason = "below stop but stronger than industry within tolerance"
            recommendation = "manual review with warning"
        else:
            status = RiskSupervisionStatus.EXIT_SUGGESTED
            should_notify = True
            reason = "below stop with weak alpha or excessive stop break"
            recommendation = "manual risk handling suggested"

    return MorningSupervisionResult(
        position_id=position.position_id,
        stock_code=position.stock_code,
        stock_name=position.stock_name,
        observed_at=observed_at,
        status=status,
        should_notify_feishu=should_notify,
        open_price=open_price,
        current_price=current_price,
        first_30m_close=current_price,
        stock_return_30m=_pct(stock_return),
        industry_return_30m=_pct(industry_return),
        industry_alpha=_pct(industry_alpha),
        stop_break_pct=_pct(stop_break_pct),
        reason=reason,
        recommendation=recommendation,
    )


def build_position_risk_matrix(positions: list[ManualPosition]) -> list[PositionRisk]:
    """Return R-risk rows for manual positions."""

    return [calculate_position_risk(position) for position in positions]


def positions_requiring_supervision(positions: list[ManualPosition]) -> list[PositionRisk]:
    """Return positions whose R-risk state needs attention."""

    return [risk for risk in build_position_risk_matrix(positions) if risk.needs_supervision]
