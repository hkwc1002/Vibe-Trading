"""Settings API for Low Absorb runtime options."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/settings", tags=["low-absorb"])


class LowAbsorbSettingsPatch(BaseModel):
    feishu_webhook: str | None = Field(default=None, min_length=1)
    config: dict[str, Any] | None = None


def _mask_webhook(webhook: str | None) -> str | None:
    if not webhook:
        return None
    if "/" in webhook:
        return f"{webhook.rsplit('/', 1)[0]}/****"
    return "****"


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
