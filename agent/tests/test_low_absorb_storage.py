"""Tests for InMemoryLowAbsorbStorage and JsonLowAbsorbStorage roundtrip."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

import pytest

from src.low_absorb.config import LowAbsorbConfig
from src.low_absorb.models import (
    CloseReport,
    CostChainComponent,
    FeishuNotificationResult,
    LowAbsorbSignal,
    ManualFill,
    ManualPosition,
    ManualTradePlan,
    NotificationType,
    PositionStatus,
    SignalStatus,
    TradePlanStatus,
)
from src.low_absorb.storage import InMemoryLowAbsorbStorage, JsonLowAbsorbStorage


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def _sample_signal(signal_id: str = "sig-601138-20260614") -> LowAbsorbSignal:
    return LowAbsorbSignal(
        signal_id=signal_id,
        trade_date=date(2026, 6, 14),
        stock_code="601138",
        stock_name="工业富联",
        branch_name="AI 服务器",
        grade="A",
        ma20_deviation_pct=Decimal("-0.032"),
        volume_ratio=Decimal("0.72"),
        lower_shadow_atr=Decimal("1.18"),
        reason="主线分支强，尾盘缩量回踩 MA20 附近",
        status=SignalStatus.CANDIDATE,
    )


def _sample_plan(plan_id: str = "plan-601138-20260614") -> ManualTradePlan:
    return ManualTradePlan(
        plan_id=plan_id,
        signal_id="sig-601138-20260614",
        trade_date=date(2026, 6, 14),
        stock_code="601138",
        stock_name="工业富联",
        entry_low=Decimal("18.60"),
        entry_high=Decimal("18.95"),
        stop_loss=Decimal("17.88"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.0035"),
        initial_risk_r=Decimal("1.0"),
        initial_risk_cny=Decimal("107.00"),
        open_stop_risk_cny=Decimal("107.00"),
        r_multiple=Decimal("0.00"),
        rationale="人工执行建议，仅用于用户自行判断。",
        manual_order_text="601138 工业富联，人工低吸区间 18.60-18.95，参考止损 17.88。",
        status=TradePlanStatus.RECOMMENDED,
    )


def _sample_fill(fill_id: str = "fill-601138-20260614") -> ManualFill:
    return ManualFill(
        fill_id=fill_id,
        plan_id="plan-601138-20260614",
        signal_id="sig-601138-20260614",
        stock_code="601138",
        stock_name="工业富联",
        actual_price=Decimal("18.78"),
        quantity=1000,
        fee=Decimal("5.00"),
        executed_at=datetime(2026, 6, 14, 14, 55),
    )


def _sample_position(position_id: str = "pos-601138-20260614") -> ManualPosition:
    return ManualPosition(
        position_id=position_id,
        plan_id="plan-601138-20260614",
        stock_code="601138",
        stock_name="工业富联",
        opened_at=datetime(2026, 6, 14, 14, 55),
        avg_cost=Decimal("18.78"),
        current_price=Decimal("18.80"),
        stop_loss=Decimal("17.88"),
        quantity=1000,
        position_pct=Decimal("0.12"),
        status=PositionStatus.ACTIVE_POSITION,
    )


def _sample_report(report_id: str = "close-20260614") -> CloseReport:
    return CloseReport(
        report_id=report_id,
        trade_date=date(2026, 6, 14),
        summary="2026-06-14 AI Low Absorb 收盘复盘",
        signals=[_sample_signal()],
        trade_plans=[_sample_plan()],
        positions=[_sample_position()],
        review_items=["复核人工成交回填"],
    )


def _sample_component(**overrides: object) -> CostChainComponent:
    base = {
        "component": "GPU (B200)",
        "cost_weight": Decimal("0.35"),
        "cost_increase_vs_previous_generation": Decimal("0.25"),
        "related_sector": "GPU/加速卡",
        "signal_weight": Decimal("0.90"),
        "data_source": "NVIDIA 官网",
        "source_type": "官方资料",
        "confidence": "high",
        "is_estimated": False,
        "as_of": date(2026, 6, 1),
    }
    base.update(overrides)
    return CostChainComponent(**base)


# ---------------------------------------------------------------------------
# InMemoryLowAbsorbStorage tests
# ---------------------------------------------------------------------------

class TestInMemoryStorage:
    """Roundtrip tests for InMemoryLowAbsorbStorage."""

    def test_seed_and_clear(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        signal = _sample_signal()
        plan = _sample_plan()
        fill = _sample_fill()
        position = _sample_position()

        storage.seed(signals=[signal], trade_plans=[plan], fills=[fill], positions=[position])
        assert len(storage.signals) == 1
        assert len(storage.trade_plans) == 1
        assert len(storage.fills) == 1
        assert len(storage.positions) == 1

        storage.clear()
        assert len(storage.signals) == 0
        assert len(storage.trade_plans) == 0
        assert len(storage.fills) == 0
        assert len(storage.positions) == 0
        assert len(storage.notifications) == 0
        assert len(storage.reports) == 0

    def test_config_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        config = storage.get_config()
        assert isinstance(config, LowAbsorbConfig)

        updated = storage.update_config({"min_market_turnover_cny": "600000000000"})
        assert updated.min_market_turnover_cny == Decimal("600000000000")

        # Verify read-back consistency
        same = storage.get_config()
        assert same.min_market_turnover_cny == Decimal("600000000000")

    def test_webhook_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        assert storage.get_webhook() is None

        storage.update_webhook("https://open.feishu.cn/hook/test")
        assert storage.get_webhook() == "https://open.feishu.cn/hook/test"

        storage.update_webhook(None)
        assert storage.get_webhook() is None

    def test_cost_chain_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        components = [_sample_component()]

        updated = storage.update_cost_chain_model("custom/manual", components)
        assert updated.version == "custom/manual"
        assert updated.is_editable is True
        assert len(updated.components) == 1

        models = storage.get_cost_chain_models()
        assert "custom/manual" in models
        assert models["custom/manual"].components[0].component == "GPU (B200)"

    def test_builtin_version_rejected(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        components = [_sample_component()]

        with pytest.raises(ValueError, match="only custom/manual"):
            storage.update_cost_chain_model("GB200 NVL72", components)

        with pytest.raises(ValueError, match="only custom/manual"):
            storage.update_cost_chain_model("GB300 NVL72", components)

    def test_notification_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        notif = FeishuNotificationResult(
            notification_type=NotificationType.NOTIFIER_TEST,
            idempotency_key="test-key",
            ok=False,
            sent=False,
            message="missing webhook",
        )
        storage.notifications[notif.idempotency_key] = notif
        assert storage.notifications["test-key"].ok is False
        assert storage.notifications["test-key"].message == "missing webhook"

    def test_report_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        report = _sample_report()
        storage.reports[report.report_id] = report

        loaded = storage.reports["close-20260614"]
        assert loaded.summary == "2026-06-14 AI Low Absorb 收盘复盘"
        assert len(loaded.signals) == 1
        assert len(loaded.review_items) == 1


# ---------------------------------------------------------------------------
# JsonLowAbsorbStorage tests
# ---------------------------------------------------------------------------

class TestJsonStorage:
    """Roundtrip tests for JsonLowAbsorbStorage."""

    def test_entities_roundtrip(self, tmp_path: object) -> None:
        path = tmp_path / "low_absorb_state.json"
        storage = JsonLowAbsorbStorage(path)

        signal = _sample_signal()
        plan = _sample_plan()
        fill = _sample_fill()
        position = _sample_position()
        report = _sample_report()

        storage.seed(signals=[signal], trade_plans=[plan], fills=[fill], positions=[position])
        storage.reports[report.report_id] = report
        storage.update_webhook("https://open.feishu.cn/hook/test")
        storage.update_config({"min_market_turnover_cny": "600000000000"})
        storage.save()

        # Reload from the same file — all entities should be present
        reloaded = JsonLowAbsorbStorage(path)
        assert len(reloaded.signals) == 1
        assert reloaded.signals["sig-601138-20260614"].stock_code == "601138"
        assert len(reloaded.trade_plans) == 1
        assert reloaded.trade_plans["plan-601138-20260614"].stock_code == "601138"
        assert len(reloaded.fills) == 1
        assert reloaded.fills["fill-601138-20260614"].stock_code == "601138"
        assert len(reloaded.positions) == 1
        assert reloaded.positions["pos-601138-20260614"].stock_code == "601138"
        assert len(reloaded.reports) == 1
        assert reloaded.reports["close-20260614"].trade_date == date(2026, 6, 14)
        assert reloaded.get_webhook() == "https://open.feishu.cn/hook/test"
        assert reloaded.get_config().min_market_turnover_cny == Decimal("600000000000")

    def test_corrupt_json_recovery(self, tmp_path: object) -> None:
        path = tmp_path / "corrupt.json"
        path.write_text("{invalid json content", encoding="utf-8")

        storage = JsonLowAbsorbStorage(path)
        assert len(storage.signals) == 0
        assert len(storage.trade_plans) == 0
        assert len(storage.fills) == 0
        assert len(storage.positions) == 0
        assert len(storage.reports) == 0
        assert len(storage.notifications) == 0

    def test_non_existent_file_loads_empty(self, tmp_path: object) -> None:
        path = tmp_path / "nonexistent.json"
        assert not path.exists()

        storage = JsonLowAbsorbStorage(path)
        assert len(storage.signals) == 0
        assert len(storage.trade_plans) == 0
        assert len(storage.fills) == 0
        assert len(storage.positions) == 0
        assert len(storage.reports) == 0
        assert len(storage.notifications) == 0

    def test_notifications_roundtrip_json(self, tmp_path: object) -> None:
        path = tmp_path / "notif_state.json"
        storage = JsonLowAbsorbStorage(path)

        result = FeishuNotificationResult(
            notification_type=NotificationType.CLOSE_REPORT,
            idempotency_key="notif-001",
            ok=True,
            sent=True,
            sent_at=datetime(2026, 6, 14, 15, 0),
            message="sent",
        )
        storage.notifications["notif-001"] = result
        storage.save()

        reloaded = JsonLowAbsorbStorage(path)
        assert len(reloaded.notifications) == 1
        assert reloaded.notifications["notif-001"].ok is True
        assert reloaded.notifications["notif-001"].message == "sent"
