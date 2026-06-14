"""Close report skeleton for Low Absorb review workflow."""

from __future__ import annotations

from datetime import date

from .models import CloseReport, LowAbsorbSignal, ManualPosition, ManualTradePlan


def build_close_report(
    *,
    report_id: str,
    trade_date: date,
    signals: list[LowAbsorbSignal],
    trade_plans: list[ManualTradePlan],
    positions: list[ManualPosition],
    review_items: list[str] | None = None,
) -> CloseReport:
    """Build a close report from manual workflow state."""

    return CloseReport(
        report_id=report_id,
        trade_date=trade_date,
        summary=f"{trade_date:%Y-%m-%d} AI Low Absorb 收盘复盘",
        signals=signals,
        trade_plans=trade_plans,
        positions=positions,
        review_items=review_items or [],
    )
