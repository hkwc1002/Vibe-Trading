"""AI-chain API skeleton for Low Absorb."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/low-absorb/chain", tags=["low-absorb"])


@router.get("")
def get_chain_matrix() -> dict[str, list[object]]:
    return {"branches": []}


@router.get("/snapshot")
def get_chain_snapshot() -> dict[str, object]:
    return {
        "branches": [],
        "stockMappings": [],
        "topologyNodes": ["GPU", "HBM", "CPO", "PCB", "Server", "Cooling", "Power", "Cabinet"],
    }
