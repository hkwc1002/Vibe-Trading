"""Close-report API for Low Absorb."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/reports", tags=["low-absorb"])


@router.get("")
def get_reports(
    trade_date: date | None = Query(default=None),
) -> dict[str, list[object]]:
    """Return all stored close reports, optionally filtered by trade_date."""
    storage = get_workbench_storage()
    reports = list(storage.reports.values())
    if trade_date is not None:
        reports = [r for r in reports if r.trade_date == trade_date]
    return {"reports": reports}
