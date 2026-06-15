"""AI-chain API skeleton for Low Absorb."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..chain_matrix import build_chain_workspace_snapshot
from ..cost_chain.models import (
    CostChainCandidate,
    CostChainCandidateStatus,
)
from ..models import CostChainComponent
from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/chain", tags=["low-absorb"])


class CostChainPatchRequest(BaseModel):
    components: list[CostChainComponent]


# ---------------------------------------------------------------------------
# Request / response models for cost chain updates
# ---------------------------------------------------------------------------

class CreateUpdateRequest(BaseModel):
    version: str
    source_type: str
    source_name: str
    confidence: Literal["high", "medium", "low"]
    components: list[CostChainComponent]


class RollbackRequest(BaseModel):
    target_version: str


# ---------------------------------------------------------------------------
# Existing endpoints
# ---------------------------------------------------------------------------

@router.get("")
def get_chain_matrix() -> dict[str, list[object]]:
    snapshot = get_chain_snapshot()
    return {
        "branches": snapshot["branches"],
        "costTable": snapshot["costTable"],
        "sectors": snapshot["sectors"],
    }


@router.get("/snapshot")
def get_chain_snapshot() -> dict[str, object]:
    storage = get_workbench_storage()
    return build_chain_workspace_snapshot(
        config=storage.get_config(),
        cost_models=storage.get_cost_chain_models(),
    )


@router.patch("/cost-models/{version:path}")
def patch_cost_chain_model(version: str, request: CostChainPatchRequest):
    storage = get_workbench_storage()
    try:
        return storage.update_cost_chain_model(version, request.components)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Cost chain update / review / rollback / audit endpoints (Batch B)
# ---------------------------------------------------------------------------

def _next_candidate_id(storage: object) -> str:
    """Generate a deterministic candidate ID."""
    return f"cand-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


@router.post("/updates")
def create_cost_chain_update(request: CreateUpdateRequest) -> CostChainCandidate:
    """Create a new REVIEW_PENDING candidate from collected data."""
    storage = get_workbench_storage()
    candidate = CostChainCandidate(
        candidate_id=_next_candidate_id(storage),
        version=request.version,
        source_type=request.source_type,
        source_name=request.source_name,
        confidence=request.confidence,
        components=request.components,
        created_at=datetime.now(),
    )
    return storage.create_candidate(candidate)


@router.get("/updates")
def list_cost_chain_updates() -> list[CostChainCandidate]:
    """List all candidates, newest first."""
    storage = get_workbench_storage()
    return storage.list_candidates()


@router.post("/updates/{candidate_id}/approve")
def approve_cost_chain_candidate(candidate_id: str) -> CostChainCandidate:
    """Approve a candidate: sets status APPROVED -> ACTIVE and promotes its version."""
    storage = get_workbench_storage()
    candidate = storage.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    try:
        return storage.update_candidate_status(
            candidate_id,
            CostChainCandidateStatus.APPROVED,
            review_note="Approved by user",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/updates/{candidate_id}/reject")
def reject_cost_chain_candidate(candidate_id: str) -> CostChainCandidate:
    """Reject a candidate: sets status REJECTED."""
    storage = get_workbench_storage()
    candidate = storage.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    try:
        return storage.update_candidate_status(
            candidate_id,
            CostChainCandidateStatus.REJECTED,
            review_note="Rejected by user",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/versions/{version}/rollback")
def rollback_cost_chain_version(version: str, request: RollbackRequest) -> dict[str, str]:
    """Rollback a cost chain version to a specific target version."""
    storage = get_workbench_storage()
    try:
        storage.rollback_to(version, request.target_version)
        return {"status": "ok", "detail": f"Rolled back {version} to {request.target_version}"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/audit")
def get_cost_chain_audit_log() -> list[object]:
    """Return the audit log of all cost chain actions."""
    storage = get_workbench_storage()
    return [entry.model_dump(mode="json") for entry in storage.get_audit_log()]
