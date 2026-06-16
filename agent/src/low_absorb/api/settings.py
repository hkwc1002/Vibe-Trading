"""Settings API for Low Absorb runtime options."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..notifier import _mask_webhook, get_send_policy
from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/settings", tags=["low-absorb"])


class LowAbsorbSettingsPatch(BaseModel):
    feishu_webhook: str | None = Field(default=None, min_length=1)
    config: dict[str, Any] | None = None


def _configured_webhook() -> str | None:
    return get_workbench_storage().get_webhook() or os.getenv("LOW_ABSORB_FEISHU_WEBHOOK")


@router.get("")
def get_settings() -> dict[str, object]:
    storage = get_workbench_storage()
    webhook = _configured_webhook()
    return {
        "config": storage.get_config().model_dump(mode="json"),
        "maskedWebhook": _mask_webhook(webhook),
        "webhookConfigured": webhook is not None,
    }


@router.patch("")
def patch_settings(request: LowAbsorbSettingsPatch) -> dict[str, object]:
    storage = get_workbench_storage()
    if request.feishu_webhook is not None:
        storage.update_webhook(request.feishu_webhook)
    if request.config:
        storage.update_config(request.config)
    return get_settings()


# ── Notification status / test / audit ──────────────────────────────────────


@router.get("/notifications/status")
def get_notification_status() -> dict[str, object]:
    """Return current Feishu send policy (real_send_enabled, webhook status, masked webhook)."""
    storage = get_workbench_storage()
    policy = get_send_policy(storage)
    return policy.model_dump(mode="json")


@router.post("/notifications/test")
def send_test_notification(force: bool = False) -> dict[str, object]:
    """Send a test Feishu notification (mock by default, real when env allows)."""
    from ..notifier import FeishuNotifier

    storage = get_workbench_storage()
    notifier = FeishuNotifier(webhook_url=storage.get_webhook(), storage=storage)
    result = notifier.send_test_notification(force=force)
    return result.model_dump(mode="json")


@router.get("/notifications/audit")
def list_notification_audits() -> dict[str, list[dict[str, object]]]:
    """Return all notification audit records."""
    storage = get_workbench_storage()
    audits = storage.list_notification_audits()
    return {"audits": [a.model_dump(mode="json") for a in audits]}
