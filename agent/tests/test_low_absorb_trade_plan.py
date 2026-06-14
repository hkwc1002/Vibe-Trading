"""Tests for trade plan creation and chain explanation fields."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.low_absorb.models import LowAbsorbSignal, SignalStatus
from src.low_absorb.trade_plan import create_manual_trade_plan


TRADE_DATE = date(2026, 6, 14)


def _signal(**overrides) -> LowAbsorbSignal:
    defaults = dict(
        signal_id="sig-601138-20260614",
        trade_date=TRADE_DATE,
        stock_code="601138",
        stock_name="工业富联",
        branch_name="服务器ODM",
        grade="A",
        ma20_deviation_pct=Decimal("0.008"),
        volume_ratio=Decimal("0.55"),
        lower_shadow_atr=Decimal("0.65"),
        reason="MA20 偏离 0.80%，5日量比 0.55",
        status=SignalStatus.CANDIDATE,
    )
    defaults.update(overrides)
    return LowAbsorbSignal(**defaults)


def test_trade_plan_includes_chain_explanation() -> None:
    signal = _signal(
        chain_explanation="AI Chain：服务器ODM 分支 RS 1.18，成本链权重 0.70，用于排序。",
        branch_strength=Decimal("1.18"),
        cost_signal_weight=Decimal("0.70"),
        priority_score=Decimal("98.80"),
    )
    plan = create_manual_trade_plan(
        signal=signal,
        trade_date=TRADE_DATE,
        entry_low=Decimal("18.62"),
        entry_high=Decimal("19.20"),
        stop_loss=Decimal("18.00"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.005"),
        initial_risk_cny=Decimal("120.00"),
        open_stop_risk_cny=Decimal("120.00"),
        chain_explanation=signal.chain_explanation,
        branch_strength=signal.branch_strength,
        cost_signal_weight=signal.cost_signal_weight,
        priority_score=signal.priority_score,
    )
    assert "服务器ODM" in plan.chain_explanation
    assert "RS" in plan.chain_explanation
    assert plan.branch_strength == Decimal("1.18")
    assert plan.cost_signal_weight == Decimal("0.70")
    assert plan.priority_score == Decimal("98.80")


def test_trade_plan_passes_downgrade_reason() -> None:
    signal = _signal(
        downgrade_reason="数据新鲜度衰减 25%，优先级已下调",
    )
    plan = create_manual_trade_plan(
        signal=signal,
        trade_date=TRADE_DATE,
        entry_low=Decimal("18.62"),
        entry_high=Decimal("19.20"),
        stop_loss=Decimal("18.00"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.005"),
        initial_risk_cny=Decimal("120.00"),
        open_stop_risk_cny=Decimal("120.00"),
        downgrade_reason=signal.downgrade_reason,
    )
    assert "新鲜度衰减" in plan.downgrade_reason
    assert "25%" in plan.downgrade_reason


def test_trade_plan_passes_block_reason() -> None:
    signal = _signal(
        block_reason="组合风险预算已满：已分配 60%，超出 60% 上限",
    )
    plan = create_manual_trade_plan(
        signal=signal,
        trade_date=TRADE_DATE,
        entry_low=Decimal("18.62"),
        entry_high=Decimal("19.20"),
        stop_loss=Decimal("18.00"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.005"),
        initial_risk_cny=Decimal("120.00"),
        open_stop_risk_cny=Decimal("120.00"),
        block_reason=signal.block_reason,
    )
    assert "风险预算已满" in plan.block_reason


def test_trade_plan_sector_role_and_rationale() -> None:
    signal = _signal(
        chain_explanation="AI Chain：服务器ODM 分支 RS 1.18。",
        sector_role="mainboard_mapping",
    )
    plan = create_manual_trade_plan(
        signal=signal,
        trade_date=TRADE_DATE,
        entry_low=Decimal("18.62"),
        entry_high=Decimal("19.20"),
        stop_loss=Decimal("18.00"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.005"),
        initial_risk_cny=Decimal("120.00"),
        open_stop_risk_cny=Decimal("120.00"),
        rationale="MA20 偏离 0.80%，量比 0.55",
        chain_explanation=signal.chain_explanation,
        sector_role=signal.sector_role,
    )
    assert plan.sector_role == "mainboard_mapping"
    assert "MA20 偏离" in plan.rationale
    assert "人工低吸区间" in plan.manual_order_text


def test_trade_plan_manual_text_contains_key_info() -> None:
    signal = _signal()
    plan = create_manual_trade_plan(
        signal=signal,
        trade_date=TRADE_DATE,
        entry_low=Decimal("18.62"),
        entry_high=Decimal("19.20"),
        stop_loss=Decimal("18.00"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.005"),
        initial_risk_cny=Decimal("120.00"),
        open_stop_risk_cny=Decimal("120.00"),
    )
    assert "601138" in plan.manual_order_text
    assert "工业富联" in plan.manual_order_text
    assert "18.62" in plan.manual_order_text
    assert "19.20" in plan.manual_order_text
    assert "18.00" in plan.manual_order_text


def test_trade_plan_empty_explanation() -> None:
    signal = _signal()
    plan = create_manual_trade_plan(
        signal=signal,
        trade_date=TRADE_DATE,
        entry_low=Decimal("18.62"),
        entry_high=Decimal("19.20"),
        stop_loss=Decimal("18.00"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.005"),
        initial_risk_cny=Decimal("120.00"),
        open_stop_risk_cny=Decimal("120.00"),
    )
    assert plan.chain_explanation == ""
    assert plan.downgrade_reason == ""
    assert plan.block_reason == ""
    assert plan.status.value == "RECOMMENDED"
