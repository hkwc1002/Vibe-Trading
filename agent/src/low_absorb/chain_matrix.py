"""AI-chain relative-strength gate helpers."""

from __future__ import annotations

from .data_provider import ChainBranchStrength
from .models import ChainBranchSnapshot


def passed_chain_branches(branches: list[ChainBranchSnapshot]) -> list[ChainBranchSnapshot]:
    """Return branch snapshots that pass the relative-strength gate."""

    return [branch for branch in branches if branch.gate_passed]


def chain_branch_allows_stock(branch_name: str, branches: list[ChainBranchStrength]) -> bool:
    """Reject a stock when its AI branch ranks last and the branch slope is negative."""

    branch = next((item for item in branches if item.branch_name == branch_name), None)
    if branch is None:
        return False
    return not (branch.rank >= branch.total_branches and branch.slope < 0)
