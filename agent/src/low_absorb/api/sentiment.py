"""Sentiment API skeleton for Low Absorb."""

from __future__ import annotations

from fastapi import APIRouter

from ..sentiment import build_sentiment_permission_snapshot
from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/sentiment", tags=["low-absorb"])


@router.get("")
def get_sentiment() -> dict[str, object]:
    return {"snapshot": get_sentiment_snapshot()}


@router.get("/snapshot")
def get_sentiment_snapshot() -> dict[str, object]:
    snapshot = build_sentiment_permission_snapshot(get_workbench_storage().get_config())
    return {
        **snapshot,
        "snapshot": {
            "compositeScore": 71,
            "macroGate": snapshot["tradingPermission"]["status"],
            "marketTurnoverCny": snapshot["instrumentPanels"][0]["value"],
            "limitBreakRate": snapshot["instrumentPanels"][1]["value"],
            "aiCapitalTemperature": snapshot["instrumentPanels"][3]["value"],
        },
    }
