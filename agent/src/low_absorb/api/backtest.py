"""Backtest API skeleton for Low Absorb."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/low-absorb/backtest", tags=["low-absorb"])


@router.get("")
def get_backtest_placeholder() -> dict[str, list[object]]:
    return {"runs": []}


@router.get("/summary")
def get_backtest_summary() -> dict[str, object]:
    return {
        "metrics": {
            "winRate": None,
            "averageR": None,
            "maxDrawdown": None,
            "sampleSize": 0,
            "profitFactor": None,
            "bestBranch": None,
        },
        "historicalSignals": [],
        "message": "backtest engine is not connected in this skeleton",
    }


@router.post("/run")
def run_backtest_placeholder() -> dict[str, object]:
    return {
        "runId": None,
        "status": "NOT_STARTED",
        "message": "real backtest execution is intentionally not implemented yet",
    }
