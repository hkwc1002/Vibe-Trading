"""Sentiment API skeleton for Low Absorb."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/low-absorb/sentiment", tags=["low-absorb"])


@router.get("")
def get_sentiment() -> dict[str, object]:
    return {"snapshot": None}


@router.get("/snapshot")
def get_sentiment_snapshot() -> dict[str, object]:
    return {
        "snapshot": {
            "compositeScore": 0,
            "macroGate": "WAITING_FOR_DATA",
            "marketTurnoverCny": None,
            "limitBreakRate": None,
            "aiCapitalTemperature": None,
        }
    }
