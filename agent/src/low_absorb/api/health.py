"""Health-check endpoints for the Low Absorb module.

Routes are registered under ``/low-absorb/health/*`` and inherit the
same authentication dependency as all other Low Absorb routes.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..deployment.config_validator import validate_production_readiness
from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/health", tags=["low-absorb"])


@router.get("/liveness")
def liveness() -> dict[str, str]:
    """Lightweight liveness check — confirms the service process is alive."""
    return {"status": "alive"}


@router.get("/readiness")
def readiness() -> dict[str, object]:
    """Production readiness check — aggregates all configuration validators.

    Returns a JSON object with a top-level ``ready`` boolean and a
    ``failures`` list.  Individual failure entries expose only fixed,
    pre-defined detail strings (``"ok"``, ``"configured"``, ``"missing"``,
    ``"fixture_fallback_forbidden"``, ``"no_active_version"``,
    ``"storage_not_writable"``) — no paths, keys, tokens, or webhook
    values are ever returned.
    """
    storage = get_workbench_storage()
    result = validate_production_readiness(storage)
    return {
        "ready": result.ready,
        "failures": [
            {"name": f.name, "ok": f.ok, "detail": f.detail}
            for f in result.failures
        ],
    }
