"""Semi-automated cost chain collector and candidate generator."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from ..chain_matrix import default_cost_chain_models
from ..models import CostChainComponent, CostChainModel
from ..storage import InMemoryLowAbsorbStorage
from .models import CostChainCandidate


def _compute_diff_summary(
    candidate_components: list[CostChainComponent],
    active_components: list[CostChainComponent],
) -> list[str]:
    """Compare candidate components against active and produce a diff summary.

    Each diff entry describes a meaningful change in cost_weight or signal_weight.
    """
    diffs: list[str] = []
    candidate_by_component = {c.component: c for c in candidate_components}
    active_by_component = {c.component: c for c in active_components}

    for comp_name, cand_comp in candidate_by_component.items():
        active_comp = active_by_component.get(comp_name)
        if active_comp is None:
            diffs.append(f"新增组件: {comp_name}")
            continue
        if cand_comp.cost_weight != active_comp.cost_weight:
            diffs.append(f"{comp_name}: 权重 {active_comp.cost_weight} → {cand_comp.cost_weight}")
        if cand_comp.signal_weight != active_comp.signal_weight:
            diffs.append(f"{comp_name}: 信号权重 {active_comp.signal_weight} → {cand_comp.signal_weight}")

    for comp_name in active_by_component:
        if comp_name not in candidate_by_component:
            diffs.append(f"移除组件: {comp_name}")

    return diffs


def collect_cost_chain_update(
    storage: InMemoryLowAbsorbStorage,
    source: str = "manual",
    source_name: str = "手动维护",
    confidence: Literal["high", "medium", "low"] = "medium",
) -> CostChainCandidate:
    """Generate a new REVIEW_PENDING candidate from current default models.

    This is a pluggable function that uses default/fixture data.
    Real HTTP-backed collection can be added later by providing a
    different source callable.
    """
    models = default_cost_chain_models()
    active_models = storage.get_cost_chain_models()

    # Use the highest-priority active model as the template
    version = "GB300 NVL72"
    model = models.get(version)
    if model is None:
        model = CostChainModel(version=version)

    # Compute diff against active version
    active_model = active_models.get(version)
    diff_summary = _compute_diff_summary(
        model.components,
        active_model.components if active_model else [],
    )

    candidate = CostChainCandidate(
        candidate_id=f"cand-auto-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        version=version,
        source_type=source,
        source_name=source_name,
        confidence=confidence,
        components=model.components,
        diff_summary=diff_summary,
        created_at=datetime.now(),
    )
    storage.create_candidate(candidate)
    return candidate
