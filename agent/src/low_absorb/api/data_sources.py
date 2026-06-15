"""Data source diagnostic API endpoints."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter

from ..data_sources.a_share_orchestrator import AShareOrchestrator

router = APIRouter(prefix="/low-absorb/data-sources", tags=["data-sources"])

_orchestrator: AShareOrchestrator | None = None


def set_data_sources_orchestrator(orch: AShareOrchestrator) -> None:
    global _orchestrator
    _orchestrator = orch


def _get_orch() -> AShareOrchestrator:
    if _orchestrator is None:
        set_data_sources_orchestrator(AShareOrchestrator())
    return _orchestrator  # type: ignore[return-value]


@router.get("/status")
def get_data_source_status() -> dict:
    """Return health status of all A-share data sources."""
    orch = _get_orch()
    health = orch.get_all_health()
    return {
        "success": True,
        "data": {
            "sources": {
                sid: {
                    "source_id": h.source_id,
                    "enabled": h.enabled,
                    "health_score": float(h.health_score),
                    "circuit_state": h.circuit_state,
                    "consecutive_failures": h.consecutive_failures,
                    "last_success_at": h.last_success_at.isoformat() if h.last_success_at else None,
                    "last_failure_at": h.last_failure_at.isoformat() if h.last_failure_at else None,
                    "cooldown_until": h.cooldown_until.isoformat() if h.cooldown_until else None,
                }
                for sid, h in health.items()
            },
            "summary": orch.get_status_summary(),
            "available_sources": orch.get_available_sources(),
        },
        "error": None,
    }


@router.post("/check")
def trigger_health_check() -> dict:
    """Trigger a manual health check cycle on all sources."""
    orch = _get_orch()
    health = orch.get_all_health()
    return {
        "success": True,
        "data": {
            "checked_at": datetime.now().isoformat(),
            "sources": {
                sid: {"source_id": h.source_id, "health_score": float(h.health_score), "circuit_state": h.circuit_state}
                for sid, h in health.items()
            },
        },
        "error": None,
    }


@router.get("/attempts")
def get_source_attempts() -> dict:
    """Return recent data source attempt and failure logs."""
    orch = _get_orch()
    health = orch.get_all_health()
    return {
        "success": True,
        "data": {
            "attempts": [
                {"source_id": sid, "circuit_state": h.circuit_state, "consecutive_failures": h.consecutive_failures, "health_score": float(h.health_score)}
                for sid, h in health.items()
            ]
        },
        "error": None,
    }
