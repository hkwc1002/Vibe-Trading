"""Feishu notification helpers for manual Low Absorb recommendations."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from .models import (
    CloseReport,
    FeishuNotificationAudit,
    FeishuNotificationResult,
    FeishuNotificationType,
    FeishuSendPolicy,
    LowAbsorbSignal,
    ManualPosition,
    ManualTradePlan,
    NotificationType,
    PositionRisk,
)
from .storage import InMemoryLowAbsorbStorage, LowAbsorbRepository

FeishuTransport = Callable[[str, dict[str, object]], tuple[int, str]]


# Regex that matches any HTTPS/HTTP URL — used to scrub sensitive URLs
# (including webhook tokens) from error messages before they reach
# API responses, logs, or audit records.
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def _safe_error(msg: str) -> str:
    """Strip URLs (and any embedded secrets) from an error message.

    Webhook tokens, API keys, or upstream URLs embedded in httpx
    exception strings or Feishu response bodies are replaced with
    ``[redacted]`` so they never appear in API responses, logs, or
    audit records.
    """
    return _URL_PATTERN.sub("[redacted]", msg)


def _mask_webhook(webhook: str | None) -> str | None:
    """Mask the sensitive portion of a Feishu webhook URL.

    Never returns a full webhook — only the host/path prefix with the
    token portion replaced by ``****``.
    """
    if not webhook:
        return None
    if "/" in webhook:
        return f"{webhook.rsplit('/', 1)[0]}/****"
    return "****"


def get_send_policy(storage: LowAbsorbRepository) -> FeishuSendPolicy:
    """Derive the current Feishu send policy from environment and storage.

    *real_send_enabled* is ``True`` only when ``LOW_ABSORB_FEISHU_REAL_SEND``
    is set to ``"1"`` or ``"true"`` (case-insensitive).  The webhook URL is
    never returned in full — only a masked form.
    """
    webhook = storage.get_webhook() or os.getenv("LOW_ABSORB_FEISHU_WEBHOOK")
    real_send = os.getenv("LOW_ABSORB_FEISHU_REAL_SEND", "").lower() in ("1", "true")
    return FeishuSendPolicy(
        real_send_enabled=real_send,
        webhook_configured=webhook is not None,
        masked_webhook=_mask_webhook(webhook),
    )


def make_feishu_result(
    *,
    notification_type: FeishuNotificationType,
    idempotency_key: str,
    sent: bool,
    message: str,
) -> FeishuNotificationResult:
    """Create a Feishu notification result without performing network I/O."""

    return FeishuNotificationResult(
        notification_id=f"fs-{uuid4().hex}",
        notification_type=notification_type,
        idempotency_key=idempotency_key,
        ok=sent,
        sent_at=datetime.now(timezone.utc) if sent else None,
        sent=sent,
        message=message,
    )


def _default_transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
    import httpx

    response = httpx.post(url, json=payload, timeout=10)
    return response.status_code, response.text


def _interactive_card(title: str, lines: list[str], *, template: str = "blue") -> dict[str, object]:
    content = "\n".join([f"**{title}**", *[f"- {line}" for line in lines]])
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": template, "title": {"tag": "plain_text", "content": title}},
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}],
        },
    }


def build_notifier_test_card() -> dict[str, object]:
    """Build the Feishu notifier test card payload."""

    return _interactive_card("AI Low Absorb 通知测试", ["飞书通知测试卡", "仅验证 webhook 和幂等配置。"])


def build_buy_recommendation_card(*, plan: ManualTradePlan, signal: LowAbsorbSignal) -> dict[str, object]:
    """Build a manual-execution recommendation card."""

    return _interactive_card(
        "14:45 低吸交易计划｜人工执行",
        [
            f"股票代码：{plan.stock_code}",
            f"股票名称：{plan.stock_name}",
            f"AI 分支：{signal.branch_name}",
            f"信号等级：{signal.grade}",
            f"建议低吸区间：{plan.entry_low} - {plan.entry_high}",
            f"参考止损：{plan.stop_loss}",
            f"建议仓位：{plan.planned_position_pct}",
            f"初始 R 风险：{plan.initial_risk_cny}",
            f"入选理由：{signal.reason}",
            "风险提示：低吸计划可能失效，请按个人风控独立判断。",
            f"可复制的人工下单信息：{plan.manual_order_text}",
            "明确声明：系统不会自动交易，请在券商 App 手动确认。",
        ],
    )


def build_close_report_card(*, report: CloseReport) -> dict[str, object]:
    """Build a close-report Feishu card."""

    pending_fills = [
        plan for plan in report.trade_plans
        if str(plan.status) not in {"TradePlanStatus.MANUAL_FILLED", "MANUAL_FILLED"}
    ]
    return _interactive_card(
        "AI 主板低吸｜收盘日报",
        [
            f"交易日期：{report.trade_date:%Y-%m-%d}",
            "市场状态：待接入市场快照",
            "两市成交额：待接入市场快照",
            "炸板率：待接入市场快照",
            "AI 资金温度：待接入市场快照",
            "最强 AI 分支：待接入产业链矩阵",
            "最弱 AI 分支：待接入产业链矩阵",
            f"今日候选：{len(report.signals)}",
            "今日失效候选：0",
            f"待人工成交回填：{len(pending_fills)}",
            f"明日 10:00 需要监督的持仓：{len(report.positions)}",
        ],
    )


def build_risk_alert_card(
    *,
    position: ManualPosition,
    risk: PositionRisk,
    first_30m_close: Decimal,
    industry_alpha: Decimal,
    supervision_status: str,
) -> dict[str, object]:
    """Build a 10:00 manual risk alert card."""

    return _interactive_card(
        "10:00 风控提醒｜人工处理",
        [
            f"股票代码：{position.stock_code}",
            f"股票名称：{position.stock_name}",
            f"持仓成本：{position.cost_price}",
            f"当前价格：{position.current_price}",
            f"止损价：{position.stop_loss}",
            f"首根 30 分钟 K 线收盘价：{first_30m_close}",
            f"行业相对 Alpha：{industry_alpha}",
            f"当前风险：{risk.current_risk_amount}",
            f"风控状态：{supervision_status}",
            "建议人工处理动作：请复核风险状态并自行处理。",
            "明确声明：系统不会自动处理持仓变化。",
        ],
        template="red",
    )


def build_fill_reminder_card(*, plan: ManualTradePlan) -> dict[str, object]:
    """Build a manual fill reminder card."""

    return _interactive_card(
        "人工成交回填提醒",
        [
            f"股票代码：{plan.stock_code}",
            f"股票名称：{plan.stock_name}",
            "请将外部券商 App 中已完成的真实成交回填到系统。",
        ],
        template="orange",
    )


class FeishuNotifier:
    """Feishu sender with idempotency, real_send toggle and audit trail."""

    def __init__(
        self,
        *,
        webhook_url: str | None = None,
        storage: LowAbsorbRepository | None = None,
        transport: FeishuTransport | None = None,
    ) -> None:
        self.webhook_url = webhook_url if webhook_url is not None else os.getenv("LOW_ABSORB_FEISHU_WEBHOOK")
        self.storage = storage or InMemoryLowAbsorbStorage()
        self.transport = transport or _default_transport

    def get_policy(self) -> FeishuSendPolicy:
        """Convenience — delegate to module-level ``get_send_policy`` with our storage."""
        return get_send_policy(self.storage)

    def _write_audit(
        self,
        result: FeishuNotificationResult,
        *,
        real_send: bool,
        target_id: str | None = None,
    ) -> None:
        """Write a ``FeishuNotificationAudit`` record for the given send result."""
        notification_type = result.notification_type
        type_str = notification_type.value if isinstance(notification_type, NotificationType) else str(notification_type)
        audit = FeishuNotificationAudit(
            notification_id=result.notification_id,
            notification_type=type_str,
            target_id=target_id,
            idempotency_key=result.idempotency_key,
            real_send=real_send,
            ok=result.ok,
            error=result.error,
            sent_at=result.sent_at,
        )
        self.storage.add_notification_audit(audit)

    def send_test_notification(self, *, force: bool = False) -> FeishuNotificationResult:
        return self._send(
            notification_type=NotificationType.NOTIFIER_TEST,
            idempotency_key="notifier-test",
            payload=build_notifier_test_card(),
            force=force,
            target_id="notifier-test",
        )

    def send_buy_recommendation(
        self,
        *,
        plan: ManualTradePlan,
        signal: LowAbsorbSignal,
        force: bool = False,
    ) -> FeishuNotificationResult:
        return self._send(
            notification_type=NotificationType.BUY_RECOMMENDATION,
            idempotency_key=f"{plan.trade_date:%Y%m%d}:{NotificationType.BUY_RECOMMENDATION}:{signal.signal_id}",
            payload=build_buy_recommendation_card(plan=plan, signal=signal),
            force=force,
            target_id=signal.signal_id,
        )

    def send_close_report(self, *, report: CloseReport, force: bool = False) -> FeishuNotificationResult:
        return self._send(
            notification_type=NotificationType.CLOSE_REPORT,
            idempotency_key=f"{report.trade_date:%Y%m%d}:{NotificationType.CLOSE_REPORT}:{report.report_id}",
            payload=build_close_report_card(report=report),
            force=force,
            target_id=report.report_id,
        )

    def send_risk_alert(
        self,
        *,
        position: ManualPosition,
        risk: PositionRisk,
        first_30m_close: Decimal,
        industry_alpha: Decimal,
        supervision_status: str,
        force: bool = False,
    ) -> FeishuNotificationResult:
        return self._send(
            notification_type=NotificationType.MORNING_RISK_ALERT,
            idempotency_key=f"{position.opened_at:%Y%m%d}:{NotificationType.MORNING_RISK_ALERT}:{position.position_id}",
            payload=build_risk_alert_card(
                position=position,
                risk=risk,
                first_30m_close=first_30m_close,
                industry_alpha=industry_alpha,
                supervision_status=supervision_status,
            ),
            force=force,
            target_id=position.position_id,
        )

    def send_fill_reminder(self, *, plan: ManualTradePlan, force: bool = False) -> FeishuNotificationResult:
        return self._send(
            notification_type=NotificationType.FILL_REMINDER,
            idempotency_key=f"{plan.trade_date:%Y%m%d}:{NotificationType.FILL_REMINDER}:{plan.plan_id}",
            payload=build_fill_reminder_card(plan=plan),
            force=force,
            target_id=plan.plan_id,
        )

    def _send(
        self,
        *,
        notification_type: NotificationType,
        idempotency_key: str,
        payload: dict[str, object],
        force: bool,
        target_id: str | None = None,
    ) -> FeishuNotificationResult:
        # ── Idempotency ────────────────────────────────────────────────────
        if not force:
            existing = self.storage.notifications.get(idempotency_key)
            if existing is not None:
                return existing.model_copy(update={"skipped": True})

        real_send_enabled = os.getenv("LOW_ABSORB_FEISHU_REAL_SEND", "").lower() in ("1", "true")

        # ── Real send path ─────────────────────────────────────────────────
        if real_send_enabled and self.webhook_url:
            try:
                status_code, body = self.transport(self.webhook_url, payload)
            except Exception as exc:  # noqa: BLE001 — notification failures must not crash workflows
                result = FeishuNotificationResult(
                    notification_id=f"fs-{uuid4().hex}",
                    ok=False,
                    notification_type=notification_type,
                    idempotency_key=idempotency_key,
                    skipped=False,
                    error="feishu_send_failed",
                    sent=False,
                    message="feishu_send_failed",
                )
                self.storage.notifications[idempotency_key] = result
                self.storage.save()
                self._write_audit(result, real_send=True, target_id=target_id)
                return result

            ok = 200 <= status_code < 300
            result = FeishuNotificationResult(
                notification_id=f"fs-{uuid4().hex}",
                ok=ok,
                notification_type=notification_type,
                idempotency_key=idempotency_key,
                sent_at=datetime.now(timezone.utc) if ok else None,
                skipped=False,
                error=None if ok else f"HTTP_{status_code}",
                sent=ok,
                message="sent" if ok else "feishu_send_failed",
            )
            self.storage.notifications[idempotency_key] = result
            self.storage.save()
            self._write_audit(result, real_send=True, target_id=target_id)
            return result

        # ── Mock path — never call transport ──────────────────────────────
        if real_send_enabled and not self.webhook_url:
            result = FeishuNotificationResult(
                notification_id=f"fs-{uuid4().hex}",
                ok=False,
                notification_type=notification_type,
                idempotency_key=idempotency_key,
                skipped=False,
                error="missing webhook",
                sent=False,
                message="missing webhook",
            )
        elif not real_send_enabled:
            result = FeishuNotificationResult(
                notification_id=f"fs-{uuid4().hex}",
                ok=True,
                notification_type=notification_type,
                idempotency_key=idempotency_key,
                sent=False,
                message="real_send_disabled",
            )
        else:
            result = FeishuNotificationResult(
                notification_id=f"fs-{uuid4().hex}",
                ok=True,
                notification_type=notification_type,
                idempotency_key=idempotency_key,
                sent=False,
                message="mock_send",
            )

        self.storage.notifications[idempotency_key] = result
        self.storage.save()
        self._write_audit(result, real_send=real_send_enabled, target_id=target_id)
        return result
