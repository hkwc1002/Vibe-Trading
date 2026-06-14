"""Tests for chain_matrix: cost chain models, snapshot, and sector workspace."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.low_absorb.chain_matrix import (
    SECTOR_TABS,
    build_chain_workspace_snapshot,
    chain_branch_allows_stock,
    chain_explanation_for_sector,
    chain_priority_score,
    cost_signal_weight_for_sector,
    default_cost_chain_models,
    normalize_chain_sector,
)
from src.low_absorb.config import LowAbsorbConfig
from src.low_absorb.data_provider import ChainBranchStrength


def test_default_cost_chain_models_returns_three_versions() -> None:
    models = default_cost_chain_models()
    assert set(models.keys()) == {"GB200 NVL72", "GB300 NVL72", "custom/manual"}


def test_builtin_models_are_not_editable() -> None:
    models = default_cost_chain_models()
    assert models["GB200 NVL72"].is_editable is False
    assert models["GB300 NVL72"].is_editable is False


def test_custom_manual_model_is_editable() -> None:
    models = default_cost_chain_models()
    assert models["custom/manual"].is_editable is True


def test_cost_chain_component_has_all_required_fields() -> None:
    """Task 3: CostChainComponent must include all 14 user-facing fields."""
    models = default_cost_chain_models()
    components = models["GB300 NVL72"].components
    assert len(components) > 0

    required_fields = {
        "component", "cost_weight", "cost_weight_range",
        "cost_increase_vs_previous_generation", "related_sector",
        "a_share_leaders", "tradable_mainboard_mapping", "signal_weight",
        "data_source", "source_type", "confidence", "as_of", "methodology_note",
    }
    for comp in components:
        missing = required_fields - set(type(comp).model_fields.keys())
        assert not missing, f"Component '{comp.component}' missing fields: {missing}"
        assert comp.component != ""
        assert comp.related_sector != ""
        assert comp.data_source != ""
        assert comp.as_of is not None


def test_cost_chain_components_have_source_and_confidence() -> None:
    """Task 3: Every component must have source_type, confidence, and as_of."""
    models = default_cost_chain_models()
    valid_source_types = {"official_spec_and_estimate", "broker_estimate", "industry_estimate", "manual", "manual_maintenance"}
    for version, model in models.items():
        for comp in model.components:
            assert comp.source_type in valid_source_types, (
                f"{version}/{comp.component}: unexpected source_type '{comp.source_type}'"
            )
            assert comp.confidence in {"high", "medium", "low"}, (
                f"{version}/{comp.component}: unexpected confidence '{comp.confidence}'"
            )
            assert isinstance(comp.as_of, date)


def test_low_confidence_data_has_estimation_note() -> None:
    """Task 3: Low-confidence data can be shown but must not decide recommendations alone."""
    models = default_cost_chain_models()
    low_conf = [
        comp for model in models.values()
        for comp in model.components
        if comp.confidence == "low"
    ]
    assert len(low_conf) > 0
    for comp in low_conf:
        assert comp.is_estimated is True or comp.methodology_note != ""


def test_build_chain_snapshot_has_all_sections() -> None:
    """Task 3/4: Snapshot includes costTable, sectors, branches, activeVersion."""
    config = LowAbsorbConfig()
    models = default_cost_chain_models()
    snapshot = build_chain_workspace_snapshot(config=config, cost_models=models)
    assert "activeVersion" in snapshot
    assert "costTable" in snapshot
    assert "sectors" in snapshot
    assert "costModels" in snapshot
    assert "branches" in snapshot
    assert len(snapshot["costTable"]) > 0


def test_sector_tabs_count_is_eight() -> None:
    """Task 4: 页面内部导航包含 8 个标签."""
    assert len(SECTOR_TABS) == 8
    ids = [t["id"] for t in SECTOR_TABS]
    expected = ["cost-overview", "gpu", "hbm", "cpo", "pcb", "odm", "cooling", "power"]
    assert ids == expected


def test_sector_workspace_at_most_five_stocks() -> None:
    """Task 4: 每个板块最多展示 5 类股票角色."""
    config = LowAbsorbConfig()
    models = default_cost_chain_models()
    snapshot = build_chain_workspace_snapshot(config=config, cost_models=models)
    for sector in snapshot.get("sectors", []):
        assert len(sector.get("stocks", [])) <= 5


def test_normalize_chain_sector() -> None:
    assert normalize_chain_sector("AI 服务器") == "服务器ODM"
    assert normalize_chain_sector("GPU") == "GPU/加速卡"
    assert normalize_chain_sector("HBM") == "HBM/存储"
    assert normalize_chain_sector("CPO") == "CPO/光模块"
    assert normalize_chain_sector("PCB") == "PCB/高速板"
    assert normalize_chain_sector("未知板块") == "未知板块"


def test_chain_branch_rejects_last_rank_negative_slope() -> None:
    branches = [
        ChainBranchStrength(branch_name="GPU/加速卡", rank=1, total_branches=3, slope=Decimal("0.05"), relative_strength=Decimal("1.2")),
        ChainBranchStrength(branch_name="HBM/存储", rank=2, total_branches=3, slope=Decimal("0.01"), relative_strength=Decimal("1.0")),
        ChainBranchStrength(branch_name="服务器ODM", rank=3, total_branches=3, slope=Decimal("-0.03"), relative_strength=Decimal("0.85")),
    ]
    assert chain_branch_allows_stock("服务器ODM", branches) is False
    assert chain_branch_allows_stock("GPU/加速卡", branches) is True


def test_chain_priority_score_combines_branch_and_cost() -> None:
    config = LowAbsorbConfig()
    branches = [
        ChainBranchStrength(branch_name="GPU/加速卡", rank=1, total_branches=3, slope=Decimal("0.08"), relative_strength=Decimal("1.30")),
    ]
    score = chain_priority_score(sector="GPU/加速卡", branches=branches, config=config)
    assert score > 0


def test_cost_signal_weight_falls_back_to_config() -> None:
    config = LowAbsorbConfig()
    weight = cost_signal_weight_for_sector("GPU/加速卡", config)
    assert weight == config.chain_cost_signal_weights.get("GPU/加速卡", Decimal("0"))


def test_chain_explanation_contains_sector_info() -> None:
    config = LowAbsorbConfig()
    branches = [
        ChainBranchStrength(branch_name="GPU/加速卡", rank=1, total_branches=3, slope=Decimal("0.08"), relative_strength=Decimal("1.30")),
    ]
    explanation = chain_explanation_for_sector(sector="GPU/加速卡", branches=branches, config=config)
    assert "GPU" in explanation or "加速卡" in explanation
