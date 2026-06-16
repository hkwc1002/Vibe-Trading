from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal

from src.low_absorb.models import (
    CloseReport,
    FeishuNotificationAudit,
    FeishuSendPolicy,
    LowAbsorbSignal,
    ManualPosition,
    ManualTradePlan,
    NotificationType,
    PositionRisk,
)
from src.low_absorb.notifier import FeishuNotifier, _mask_webhook, _safe_error, get_send_policy
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

    # With real_send disabled (default), mock returns ok=True
    assert result.ok is True
    assert result.notification_type == NotificationType.NOTIFIER_TEST
    assert result.skipped is False
    assert result.message == "real_send_disabled"


def test_send_test_notification_without_webhook_returns_error_when_real_send_enabled() -> None:
    """When real_send is enabled but no webhook, returns error."""
    notifier = FeishuNotifier(webhook_url=None, storage=InMemoryLowAbsorbStorage())

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        result = notifier.send_test_notification()
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

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

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        first = notifier.send_buy_recommendation(plan=_plan(), signal=_signal())
        second = notifier.send_buy_recommendation(plan=_plan(), signal=_signal())
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

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

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        notifier.send_buy_recommendation(plan=_plan(), signal=_signal())
        forced = notifier.send_buy_recommendation(plan=_plan(), signal=_signal(), force=True)
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

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

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        result = notifier.send_close_report(report=report)
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

    assert result.ok is True
    text = str(calls[0])
    assert "AI 主板低吸｜收盘日报" in text
    assert "交易日期：2026-06-12" in text
    assert "今日候选：1" in text
    assert "待人工成交回填" in text
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

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        result = notifier.send_risk_alert(
            position=_position(),
            risk=_risk(),
            first_30m_close=Decimal("17.80"),
            industry_alpha=Decimal("-0.03"),
            supervision_status="EXIT_SUGGESTED",
        )
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

    assert result.ok is False
    assert result.notification_type == NotificationType.MORNING_RISK_ALERT
    assert result.error == "HTTP_500"
    assert result.message == "feishu_send_failed"


# ── Real-send toggle & audit tests ─────────────────────────────────────────


def test_real_send_disabled_does_not_call_transport() -> None:
    """When LOW_ABSORB_FEISHU_REAL_SEND is not set, _send must mock and not call transport."""
    calls: list[dict[str, object]] = []

    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        calls.append({"url": url, "payload": payload})
        return 200, "ok"

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/test",
        storage=storage,
        transport=transport,
    )

    # Ensure env is explicitly false
    old = os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)
    try:
        result = notifier.send_test_notification()
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old

    assert result.ok is True
    assert result.sent is False
    assert result.message == "real_send_disabled"
    assert len(calls) == 0  # transport never called


def test_real_send_enabled_calls_transport() -> None:
    """When LOW_ABSORB_FEISHU_REAL_SEND=true, _send should call transport."""
    calls: list[dict[str, object]] = []

    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        calls.append({"url": url, "payload": payload})
        return 200, "ok"

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/test",
        storage=storage,
        transport=transport,
    )

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        result = notifier.send_test_notification()
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

    assert result.ok is True
    assert result.sent is True
    assert len(calls) == 1


def test_real_send_enabled_without_webhook_returns_error() -> None:
    """When real_send is enabled but no webhook is set, _send must return error."""
    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(webhook_url=None, storage=storage)

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        result = notifier.send_test_notification()
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

    assert result.ok is False
    assert result.error == "missing webhook"


def test_get_send_policy_returns_correct_policy() -> None:
    """get_send_policy should return a FeishuSendPolicy with masked webhook."""
    storage = InMemoryLowAbsorbStorage()
    storage.update_webhook("https://open.feishu.cn/webhook/abc123")

    policy = get_send_policy(storage)

    assert isinstance(policy, FeishuSendPolicy)
    assert policy.webhook_configured is True
    assert policy.masked_webhook == "https://open.feishu.cn/webhook/****"
    assert policy.masked_webhook is not None
    assert "abc123" not in (policy.masked_webhook or "")


def test_mask_webhook_never_exposes_token() -> None:
    """_mask_webhook must never return the full webhook token."""
    assert _mask_webhook(None) is None
    assert _mask_webhook("") is None
    result = _mask_webhook("https://open.feishu.cn/webhook/secret123")
    assert result == "https://open.feishu.cn/webhook/****"
    assert "secret123" not in (result or "")
    # Plain URL (no slash after host) also masked
    assert _mask_webhook("no-slash") == "****"
    assert "no-slash" not in "****"


def test_safe_error_redacts_urls() -> None:
    """_safe_error must strip URLs from error messages to prevent webhook token leaks."""
    assert "redacted" in _safe_error("httpx error at https://open.feishu.cn/webhook/abc123")
    assert "https://" not in _safe_error("httpx error at https://open.feishu.cn/webhook/abc123")
    assert "abc123" not in _safe_error("httpx error at https://open.feishu.cn/webhook/abc123")
    # Multiple URLs
    result = _safe_error("first https://a.com/tok1 then https://b.com/tok2")
    assert result.count("[redacted]") == 2
    # No URL → unchanged
    assert _safe_error("simple error") == "simple error"
    # Empty string
    assert _safe_error("") == ""


def test_real_send_exception_does_not_leak_url() -> None:
    """When transport raises an exception, error/message must be a fixed safe string, not the raw exception."""
    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        msg = f"Connection failed. URL: '{url}'"
        raise ConnectionError(msg)

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/secret-token-12345",
        storage=storage,
        transport=transport,
    )

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        result = notifier.send_test_notification()
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

    assert result.ok is False
    # Must be a fixed safe string — no raw exception text, no URL, no token
    assert result.error == "feishu_send_failed"
    assert result.message == "feishu_send_failed"
    assert "secret-token-12345" not in (result.error or "")
    assert "secret-token-12345" not in (result.message or "")
    # Audit record must also be safe
    audits = storage.list_notification_audits()
    assert len(audits) >= 1
    latest = audits[-1]
    assert latest.error == "feishu_send_failed" or latest.error is None


def test_real_send_http_error_does_not_leak_body() -> None:
    """When transport returns non-2xx, only status code is returned — no body, no URL, no token."""
    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        return 403, '{"error":"invalid webhook","token":"abc123","secret":"my-api-key-12345"}'

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/sensitive",
        storage=storage,
        transport=transport,
    )

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        result = notifier.send_test_notification()
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

    assert result.ok is False
    # Must only expose status code — no body, no token, no key
    assert result.error == "HTTP_403"
    assert result.message == "feishu_send_failed"
    # Raw body content must NOT appear anywhere
    assert "abc123" not in (result.error or "")
    assert "abc123" not in (result.message or "")
    assert "my-api-key-12345" not in (result.error or "")
    assert "my-api-key-12345" not in (result.message or "")
    assert "invalid webhook" not in (result.error or "")


def test_notification_audit_written_after_mock_send() -> None:
    """After a mock send, a FeishuNotificationAudit must exist in storage."""
    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/webhook/test", storage=storage)

    old = os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)
    try:
        result = notifier.send_test_notification()
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old

    # Check audit was written
    audits = storage.list_notification_audits()
    assert len(audits) == 1
    audit = audits[0]
    assert isinstance(audit, FeishuNotificationAudit)
    assert audit.notification_id == result.notification_id
    assert audit.notification_type == NotificationType.NOTIFIER_TEST.value
    assert audit.idempotency_key == "notifier-test"
    assert audit.real_send is False
    assert audit.ok is True


def test_notification_audit_written_after_real_send() -> None:
    """After a real send, audit record should show real_send=True."""
    calls: list[dict[str, object]] = []

    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        calls.append(payload)
        return 200, "ok"

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/test",
        storage=storage,
        transport=transport,
    )

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        result = notifier.send_test_notification()
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

    audits = storage.list_notification_audits()
    assert len(audits) == 1
    audit = audits[0]
    assert audit.real_send is True
    assert audit.ok is True
    assert audit.sent_at is not None


def test_notification_audit_eviction() -> None:
    """When notification_audits exceed MAX_NOTIFICATION_AUDITS, oldest records are evicted."""
    from src.low_absorb.storage import MAX_NOTIFICATION_AUDITS

    storage = InMemoryLowAbsorbStorage()
    # Fill beyond capacity
    for i in range(MAX_NOTIFICATION_AUDITS + 10):
        audit = FeishuNotificationAudit(
            notification_id=f"fs-{i:04d}",
            notification_type="NOTIFIER_TEST",
            idempotency_key=f"test-{i}",
            real_send=False,
            ok=True,
            sent_at=datetime(2026, 1, 1, 0, 0, 0),
        )
        storage.add_notification_audit(audit)

    assert len(storage.notification_audits) == MAX_NOTIFICATION_AUDITS
    # The first 10 (oldest) should have been evicted
    ids = [a.notification_id for a in storage.notification_audits]
    assert "fs-0000" not in ids
    assert f"fs-{MAX_NOTIFICATION_AUDITS + 9:04d}" in ids  # newest retained


def test_notification_audit_json_persistence_roundtrip() -> None:
    """Notification audits must persist through JsonLowAbsorbStorage save/load cycle."""
    import tempfile

    from src.low_absorb.storage import JsonLowAbsorbStorage

    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(path)

    storage = JsonLowAbsorbStorage(path)
    notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/webhook/test", storage=storage)
    notifier.send_test_notification(force=True)

    memory_count = len(storage.list_notification_audits())
    # Destroy and reload from the same JSON path
    del storage

    storage2 = JsonLowAbsorbStorage(path)
    disk_count = len(storage2.list_notification_audits())

    os.unlink(path)

    assert memory_count == 1
    assert disk_count == 1
    record = storage2.list_notification_audits()[0]
    assert record.notification_type == "NOTIFIER_TEST"
    assert record.idempotency_key == "notifier-test"
