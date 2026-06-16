"""Env-guarded real Feishu integration test.

These tests ONLY fire when both ``LOW_ABSORB_FEISHU_WEBHOOK`` and
``LOW_ABSORB_FEISHU_REAL_SEND=true`` are present in the environment.
In all other cases they are skipped so CI and local dev are never
accidentally flooded with real Feishu notifications.
"""

from __future__ import annotations

import os

import pytest

from src.low_absorb.models import FeishuNotificationResult, NotificationType
from src.low_absorb.notifier import FeishuNotifier
from src.low_absorb.storage import InMemoryLowAbsorbStorage

pytestmark = pytest.mark.skipif(
    condition=os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND", "").lower()
    not in ("1", "true"),
    reason="LOW_ABSORB_FEISHU_REAL_SEND is not set to true — real Feishu send disabled",
)


def test_real_feishu_send_of_test_card() -> None:
    """Send a real test card to the configured webhook and confirm 200."""
    webhook = os.environ.get("LOW_ABSORB_FEISHU_WEBHOOK")
    if not webhook:
        pytest.skip("LOW_ABSORB_FEISHU_WEBHOOK not set — cannot send real notification")

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(webhook_url=webhook, storage=storage)

    result = notifier.send_test_notification()

    assert isinstance(result, FeishuNotificationResult)
    assert result.ok is True
    assert result.sent is True
    assert result.skipped is False
    assert result.error is None

    # Verify audit was written
    audits = storage.list_notification_audits()
    assert len(audits) == 1
    audit = audits[0]
    assert audit.real_send is True
    assert audit.ok is True
    assert audit.sent_at is not None
    assert audit.notification_type == NotificationType.NOTIFIER_TEST.value


def test_real_feishu_send_creates_audit_record() -> None:
    """Verify audit trail exists after a real send."""
    webhook = os.environ.get("LOW_ABSORB_FEISHU_WEBHOOK")
    if not webhook:
        pytest.skip("LOW_ABSORB_FEISHU_WEBHOOK not set — cannot send real notification")

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(webhook_url=webhook, storage=storage)

    result = notifier.send_test_notification(force=True)  # force to get a fresh send

    audits = storage.list_notification_audits()
    latest = audits[-1]
    assert latest.notification_id == result.notification_id
    assert latest.idempotency_key == "notifier-test"
    assert latest.real_send is True
    assert latest.ok is True
