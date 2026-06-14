"""AI-chain API skeleton for Low Absorb."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..chain_matrix import build_chain_workspace_snapshot
from ..models import CostChainComponent
from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/chain", tags=["low-absorb"])


class CostChainPatchRequest(BaseModel):
    components: list[CostChainComponent]


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
