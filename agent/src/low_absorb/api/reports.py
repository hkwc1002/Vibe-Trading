"""Close-report API skeleton for Low Absorb."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/low-absorb/reports", tags=["low-absorb"])


@router.get("")
def get_reports() -> dict[str, list[object]]:
    return {"reports": []}
