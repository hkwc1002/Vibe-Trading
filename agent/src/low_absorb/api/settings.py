"""Settings API for Low Absorb runtime options."""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..config import LowAbsorbConfig

router = APIRouter(prefix="/low-absorb/settings", tags=["low-absorb"])


class LowAbsorbSettingsPatch(BaseModel):
    feishu_webhook: str | None = Field(default=None, min_length=1)


def _mask_webhook(webhook: str | None) -> str | None:
    if not webhook:
        return None
    if "/" in webhook:
        return f"{webhook.rsplit('/', 1)[0]}/****"
    return "****"


@router.get("")
def get_settings() -> dict[str, object]:
    return {
        "config": LowAbsorbConfig(),
        "maskedWebhook": _mask_webhook(os.getenv("LOW_ABSORB_FEISHU_WEBHOOK")),
    }


@router.patch("")
def patch_settings(request: LowAbsorbSettingsPatch) -> dict[str, object]:
    if request.feishu_webhook is not None:
        os.environ["LOW_ABSORB_FEISHU_WEBHOOK"] = request.feishu_webhook
    return get_settings()
