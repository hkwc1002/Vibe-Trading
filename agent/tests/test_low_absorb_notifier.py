from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from src.low_absorb.models import (
    CloseReport,
    LowAbsorbSignal,
    ManualPosition,
    ManualTradePlan,
    NotificationType,
    PositionRisk,
)
from src.low_absorb.notifier import FeishuNotifier
from src.low_absorb.storage import InMemoryLowAbsorbStorage


def _signal() -> LowAbsorbSignal:
    return LowAbsorbSignal(
        signal_id="sig-601138-20260612",
        trade_date=date(2026, 6, 12),
        stock_code="601138",
        stock_name="工业富联",
        branch_name="AI 服务器",
        grade="A",
        ma20_deviation_pct=Decimal("-0.032"),
        volume_ratio=Decimal("0.72"),
        lower_shadow_atr=Decimal("1.18"),
        reason="主线分支强，尾盘缩量回踩 MA20 附近",
    )


def _plan() -> ManualTradePlan:
    signal = _signal()
    return ManualTradePlan(
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
        initial_risk_cny=Decimal("107.00"),
        open_stop_risk_cny=Decimal("107.00"),
        rationale="主线分支强，尾盘缩量回踩 MA20 附近。",
        manual_order_text="601138 工业富联，人工低吸区间 18.60-18.95，参考止损 17.88。",
    )


def _position() -> ManualPosition:
    return ManualPosition(
        position_id="pos-601138-20260612",
        plan_id="plan-601138-20260612",
        stock_code="601138",
        stock_name="工业富联",
        opened_at=datetime(2026, 6, 12, 14, 55),
        cost_price=Decimal("18.78"),
        current_price=Decimal("18.20"),
        stop_loss=Decimal("17.88"),
        quantity=1000,
        position_pct=Decimal("0.12"),
    )


def _risk() -> PositionRisk:
    return PositionRisk(
        stock_code="601138",
        stock_name="工业富联",
        initial_risk_amount=Decimal("900.00"),
        current_risk_amount=Decimal("320.00"),
        r_multiple=Decimal("-0.64"),
        risk_level="warning",
        needs_supervision=True,
    )


def test_send_test_notification_without_webhook_fails_gracefully() -> None:
    notifier = FeishuNotifier(webhook_url=None, storage=InMemoryLowAbsorbStorage())

    result = notifier.send_test_notification()

    assert result.ok is False
    assert result.notification_type == NotificationType.NOTIFIER_TEST
    assert result.skipped is False
    assert result.error == "missing webhook"


def test_buy_recommendation_card_format_and_idempotency() -> None:
    calls: list[dict[str, object]] = []

    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        calls.append({"url": url, "payload": payload})
        return 200, "ok"

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/webhook/test", storage=storage, transport=transport)

    first = notifier.send_buy_recommendation(plan=_plan(), signal=_signal())
    second = notifier.send_buy_recommendation(plan=_plan(), signal=_signal())

    assert first.ok is True
    assert second.ok is True
    assert second.skipped is True
    assert len(calls) == 1
    text = str(calls[0]["payload"])
    assert "14:45 低吸交易计划｜人工执行" in text
    assert "601138" in text
    assert "工业富联" in text
    assert "AI 服务器" in text
    assert "建议低吸区间" in text
    assert "系统不会自动交易" in text
    assert "人工低吸区间 18.60-18.95" in text
    assert "立即买入" not in text
    assert "一键下单" not in text
    assert "自动交易" not in text.replace("系统不会自动交易", "")


def test_force_resend_bypasses_idempotency() -> None:
    calls: list[dict[str, object]] = []

    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        calls.append(payload)
        return 200, "ok"

    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/test",
        storage=InMemoryLowAbsorbStorage(),
        transport=transport,
    )

    notifier.send_buy_recommendation(plan=_plan(), signal=_signal())
    forced = notifier.send_buy_recommendation(plan=_plan(), signal=_signal(), force=True)

    assert forced.ok is True
    assert forced.skipped is False
    assert len(calls) == 2


def test_close_report_card_format() -> None:
    calls: list[dict[str, object]] = []

    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        calls.append(payload)
        return 200, "ok"

    report = CloseReport(
        report_id="close-20260612",
        trade_date=date(2026, 6, 12),
        summary="收盘复盘",
        signals=[_signal()],
        trade_plans=[_plan()],
        positions=[_position()],
        review_items=["明日 10:00 监督工业富联"],
    )
    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/test",
        storage=InMemoryLowAbsorbStorage(),
        transport=transport,
    )

    result = notifier.send_close_report(report=report)

    assert result.ok is True
    text = str(calls[0])
    assert "AI 主板低吸｜收盘日报" in text
    assert "交易日期：2026-06-12" in text
    assert "今日候选：1" in text
    assert "待人工成交回填" in text


def test_risk_alert_card_format_and_http_failure_graceful() -> None:
    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        return 500, "server error"

    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/test",
        storage=InMemoryLowAbsorbStorage(),
        transport=transport,
    )

    result = notifier.send_risk_alert(
        position=_position(),
        risk=_risk(),
        first_30m_close=Decimal("17.80"),
        industry_alpha=Decimal("-0.03"),
        supervision_status="EXIT_SUGGESTED",
    )

    assert result.ok is False
    assert result.notification_type == NotificationType.MORNING_RISK_ALERT
    assert result.error == "HTTP 500: server error"
