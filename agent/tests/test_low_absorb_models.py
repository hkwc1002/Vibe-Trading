from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.low_absorb.models import (
    ChainBranchSnapshot,
    CloseReport,
    FeishuNotificationResult,
    LowAbsorbSignal,
    ManualFill,
    ManualPosition,
    ManualTradePlan,
    PositionRisk,
    PositionStatus,
    SentimentSnapshot,
    SignalStatus,
    TradePlanStatus,
)


def test_low_absorb_models_validate_manual_trade_flow() -> None:
    signal = LowAbsorbSignal(
        signal_id="sig-601138-20260612",
        trade_date=date(2026, 6, 12),
        stock_code="601138",
        stock_name="工业富联",
        branch_name="AI 服务器",
        grade="A",
        ma20_deviation_pct=Decimal("-3.2"),
        volume_ratio=Decimal("0.72"),
        lower_shadow_atr=Decimal("1.18"),
        reason="主线分支强，尾盘缩量回踩 MA20 附近",
        status=SignalStatus.CANDIDATE,
    )

    plan = ManualTradePlan(
        plan_id="plan-601138-20260612",
        signal_id=signal.signal_id,
        trade_date=signal.trade_date,
        stock_code=signal.stock_code,
        stock_name=signal.stock_name,
        entry_low=Decimal("18.60"),
        entry_high=Decimal("18.95"),
        stop_loss=Decimal("17.88"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.0035"),
        initial_risk_r=Decimal("1.0"),
        manual_order_text="601138 工业富联，人工低吸区间 18.60-18.95，参考止损 17.88。",
        status=TradePlanStatus.RECOMMENDED,
    )

    fill = ManualFill(
        fill_id="fill-601138-20260612",
        plan_id=plan.plan_id,
        filled_at=datetime(2026, 6, 12, 14, 55),
        stock_code=plan.stock_code,
        stock_name=plan.stock_name,
        fill_price=Decimal("18.78"),
        quantity=1000,
        fees=Decimal("5.00"),
    )

    position = ManualPosition(
        position_id="pos-601138-20260612",
        plan_id=plan.plan_id,
        stock_code=plan.stock_code,
        stock_name=plan.stock_name,
        opened_at=fill.filled_at,
        cost_price=fill.fill_price,
        current_price=Decimal("18.92"),
        stop_loss=plan.stop_loss,
        quantity=fill.quantity,
        position_pct=plan.planned_position_pct,
        status=PositionStatus.ACTIVE_POSITION,
    )

    sentiment = SentimentSnapshot(
        trade_date=signal.trade_date,
        snapshot_at=datetime(2026, 6, 12, 14, 45),
        macro_score=Decimal("0.35"),
        gate_passed=True,
        summary="宏观情绪门控通过",
    )
    branch = ChainBranchSnapshot(
        trade_date=signal.trade_date,
        branch_name=signal.branch_name,
        relative_strength=Decimal("1.18"),
        gate_passed=True,
        leaders=["601138"],
    )
    report = CloseReport(
        report_id="report-20260612",
        trade_date=signal.trade_date,
        summary="收盘后复盘等待人工成交回填",
        signals=[signal],
        trade_plans=[plan],
        positions=[position],
        review_items=["复核 10:00 监督结果"],
    )
    notification = FeishuNotificationResult(
        notification_id="fs-001",
        notification_type="buy_recommendation",
        idempotency_key="plan-601138-20260612",
        sent=True,
        message="已推送飞书推荐卡",
    )
    risk = PositionRisk(
        stock_code=position.stock_code,
        stock_name=position.stock_name,
        initial_risk_amount=Decimal("900.00"),
        current_risk_amount=Decimal("1040.00"),
        r_multiple=Decimal("0.16"),
        risk_level="watch",
        needs_supervision=True,
    )

    assert signal.status is SignalStatus.CANDIDATE
    assert plan.status is TradePlanStatus.RECOMMENDED
    assert fill.quantity == 1000
    assert position.status is PositionStatus.ACTIVE_POSITION
    assert sentiment.gate_passed is True
    assert branch.leaders == ["601138"]
    assert report.signals[0].stock_code == "601138"
    assert notification.sent is True
    assert risk.needs_supervision is True


def test_low_absorb_models_reject_non_mainboard_code_and_invalid_plan() -> None:
    with pytest.raises(ValidationError, match="mainboard"):
        LowAbsorbSignal(
            signal_id="sig-300001",
            trade_date=date(2026, 6, 12),
            stock_code="300001",
            stock_name="特锐德",
            branch_name="AI 服务器",
            grade="A",
            ma20_deviation_pct=Decimal("-2.0"),
            volume_ratio=Decimal("0.8"),
            lower_shadow_atr=Decimal("1.1"),
            reason="创业板样例应被主板过滤拒绝",
        )

    with pytest.raises(ValidationError, match="entry_high"):
        ManualTradePlan(
            plan_id="plan-invalid",
            signal_id="sig-601138",
            trade_date=date(2026, 6, 12),
            stock_code="601138",
            stock_name="工业富联",
            entry_low=Decimal("18.95"),
            entry_high=Decimal("18.60"),
            stop_loss=Decimal("17.88"),
            planned_position_pct=Decimal("0.12"),
            max_risk_pct=Decimal("0.0035"),
            initial_risk_r=Decimal("1.0"),
            manual_order_text="人工低吸计划",
        )

    with pytest.raises(ValidationError, match="stop_loss"):
        ManualTradePlan(
            plan_id="plan-invalid-stop",
            signal_id="sig-601138",
            trade_date=date(2026, 6, 12),
            stock_code="601138",
            stock_name="工业富联",
            entry_low=Decimal("18.60"),
            entry_high=Decimal("18.95"),
            stop_loss=Decimal("18.80"),
            planned_position_pct=Decimal("0.12"),
            max_risk_pct=Decimal("0.0035"),
            initial_risk_r=Decimal("1.0"),
            manual_order_text="人工低吸计划",
        )


def test_low_absorb_state_enums_cover_manual_execution_flow() -> None:
    flow = [
        "CANDIDATE",
        "RECOMMENDED",
        "SENT_TO_FEISHU",
        "MANUAL_FILLED",
        "ACTIVE_POSITION",
        "HOLDING_REVIEW",
        "EXIT_SUGGESTED",
        "MANUAL_EXITED",
        "CLOSED",
        "INVALIDATED",
    ]

    enum_values = {
        *(status.value for status in SignalStatus),
        *(status.value for status in TradePlanStatus),
        *(status.value for status in PositionStatus),
    }

    assert enum_values.issuperset(flow)
