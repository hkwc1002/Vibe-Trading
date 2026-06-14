"""Tests for chain API: snapshot, custom/manual update, and built-in rejection."""

from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.api import register_low_absorb_routes
from src.low_absorb.api.workbench import set_workbench_storage
from src.low_absorb.storage import InMemoryLowAbsorbStorage


def _client() -> TestClient:
    storage = InMemoryLowAbsorbStorage()
    set_workbench_storage(storage)
    app = FastAPI()
    register_low_absorb_routes(app)
    return TestClient(app)


def _sample_component(**overrides) -> dict:
    base = {
        "component": "GPU (B200)",
        "cost_weight": 0.35,
        "cost_weight_range": [0.30, 0.40],
        "cost_increase_vs_previous_generation": 0.25,
        "related_sector": "GPU/加速卡",
        "a_share_leaders": ["景嘉微"],
        "tradable_mainboard_mapping": ["景嘉微"],
        "signal_weight": 0.90,
        "data_source": "NVIDIA 官网",
        "source_type": "官方资料",
        "source_url": "https://www.nvidia.com",
        "source_title": "GB300 NVL72 产品页",
        "confidence": "high",
        "is_estimated": False,
        "methodology_note": "",
        "as_of": "2026-06-01",
    }
    base.update(overrides)
    return base


def test_chain_snapshot_returns_valid_structure() -> None:
    client = _client()
    response = client.get("/low-absorb/chain/snapshot")
    assert response.status_code == 200
    body = response.json()
    assert "activeVersion" in body
    assert "costTable" in body
    assert "sectors" in body
    assert "costModels" in body


def test_chain_snapshot_cost_table_has_required_columns() -> None:
    client = _client()
    body = client.get("/low-absorb/chain/snapshot").json()
    cost_table = body["costTable"]
    assert len(cost_table) > 0
    row = cost_table[0]
    assert "component" in row
    assert "cost_weight" in row
    assert "related_sector" in row
    assert "confidence" in row
    assert "as_of" in row


def test_patch_custom_manual_succeeds() -> None:
    """Task 3: custom/manual version can be updated."""
    client = _client()
    components = [_sample_component()]
    response = client.patch(
        "/low-absorb/chain/cost-models/custom/manual",
        json={"components": components},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "custom/manual"
    assert body["is_editable"] is True
    assert len(body["components"]) == 1
    assert body["components"][0]["component"] == "GPU (B200)"


def test_patch_builtin_gb200_rejected() -> None:
    """Task 3: Built-in GB200 NVL72 cannot be updated via API."""
    client = _client()
    response = client.patch(
        "/low-absorb/chain/cost-models/GB200 NVL72",
        json={"components": [_sample_component()]},
    )
    assert response.status_code == 400


def test_patch_builtin_gb300_rejected() -> None:
    """Task 3: Built-in GB300 NVL72 cannot be updated via API."""
    client = _client()
    response = client.patch(
        "/low-absorb/chain/cost-models/GB300 NVL72",
        json={"components": [_sample_component()]},
    )
    assert response.status_code == 400


def test_patch_custom_manual_updates_snapshot() -> None:
    """After updating custom/manual, the snapshot reflects new components."""
    client = _client()
    components = [_sample_component(cost_weight=0.50, signal_weight=0.80)]
    client.patch("/low-absorb/chain/cost-models/custom/manual", json={"components": components})

    snapshot = client.get("/low-absorb/chain/snapshot").json()
    cost_models = snapshot["costModels"]
    # costModels is a list of {version, is_editable, components}
    custom_models = [m for m in cost_models if m.get("version") == "custom/manual"]
    assert len(custom_models) == 1
    assert len(custom_models[0]["components"]) == 1
    assert float(custom_models[0]["components"][0]["cost_weight"]) == 0.50


def test_chain_matrix_endpoint_returns_branches_and_sectors() -> None:
    client = _client()
    response = client.get("/low-absorb/chain")
    assert response.status_code == 200
    body = response.json()
    assert "branches" in body
    assert "costTable" in body
    assert "sectors" in body


def test_patch_response_exposes_no_sensitive_data() -> None:
    """Task 3: 保存响应不得暴露密钥、Webhook 或其他敏感信息."""
    client = _client()
    response = client.patch(
        "/low-absorb/chain/cost-models/custom/manual",
        json={"components": [_sample_component()]},
    )
    body_str = str(response.json())
    assert "webhook" not in body_str.lower()
    assert "token" not in body_str.lower()
    assert "password" not in body_str.lower()
