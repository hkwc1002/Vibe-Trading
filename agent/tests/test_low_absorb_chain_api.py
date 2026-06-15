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


# ---------------------------------------------------------------------------
# Cost chain update/approve/reject/rollback/audit API tests (Batch B)
# ---------------------------------------------------------------------------

class TestChainUpdates:
    def test_create_candidate_via_api(self) -> None:
        client = _client()
        response = client.post(
            "/low-absorb/chain/updates",
            json={
                "version": "GB300 NVL72",
                "source_type": "manual",
                "source_name": "手动维护",
                "confidence": "medium",
                "components": [_sample_component()],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "REVIEW_PENDING"
        assert "candidate_id" in body

    def test_list_candidates(self) -> None:
        client = _client()
        client.post(
            "/low-absorb/chain/updates",
            json={
                "version": "GB300 NVL72",
                "source_type": "manual",
                "source_name": "手动维护",
                "confidence": "medium",
                "components": [_sample_component()],
            },
        )
        response = client.get("/low-absorb/chain/updates")
        assert response.status_code == 200
        body = response.json()
        assert len(body) >= 1

    def test_approve_candidate(self) -> None:
        client = _client()
        create_resp = client.post(
            "/low-absorb/chain/updates",
            json={
                "version": "GB300 NVL72",
                "source_type": "manual",
                "source_name": "手动维护",
                "confidence": "high",
                "components": [_sample_component()],
            },
        )
        candidate_id = create_resp.json()["candidate_id"]
        resp = client.post(f"/low-absorb/chain/updates/{candidate_id}/approve")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ACTIVE"

    def test_reject_candidate(self) -> None:
        client = _client()
        create_resp = client.post(
            "/low-absorb/chain/updates",
            json={
                "version": "GB300 NVL72",
                "source_type": "automatic",
                "source_name": "自动采集",
                "confidence": "low",
                "components": [_sample_component()],
            },
        )
        candidate_id = create_resp.json()["candidate_id"]
        resp = client.post(f"/low-absorb/chain/updates/{candidate_id}/reject")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "REJECTED"

    def test_approve_nonexistent_candidate_returns_404(self) -> None:
        client = _client()
        resp = client.post("/low-absorb/chain/updates/nonexistent/approve")
        assert resp.status_code == 404

    def test_reject_nonexistent_candidate_returns_404(self) -> None:
        client = _client()
        resp = client.post("/low-absorb/chain/updates/nonexistent/reject")
        assert resp.status_code == 404

    def test_rollback_version_deactivates_current(self) -> None:
        """POST rollback marks current_version as ROLLED_BACK in snapshot."""
        client = _client()
        # Get snapshot before rollback
        snap_before = client.get("/low-absorb/chain/snapshot").json()
        gb300_before = next(m for m in snap_before["costModels"] if m["version"] == "GB300 NVL72")
        assert gb300_before["status"] is None  # active before

        resp = client.post("/low-absorb/chain/versions/GB300 NVL72/rollback", json={"target_version": "GB200 NVL72"})
        assert resp.status_code == 200

        snap_after = client.get("/low-absorb/chain/snapshot").json()
        gb300_after = next(m for m in snap_after["costModels"] if m["version"] == "GB300 NVL72")
        assert gb300_after["status"] == "ROLLED_BACK"

    def test_rollback_version_restores_target(self) -> None:
        """POST rollback keeps target_version's components unchanged and explicitly ACTIVE."""
        client = _client()
        snap_before = client.get("/low-absorb/chain/snapshot").json()
        gb200_before = next(m for m in snap_before["costModels"] if m["version"] == "GB200 NVL72")
        gb200_gpu_weight_before = gb200_before["components"][0]["cost_weight"]
        gb300_before = next(m for m in snap_before["costModels"] if m["version"] == "GB300 NVL72")
        gb300_gpu_weight_before = gb300_before["components"][0]["cost_weight"]
        assert gb200_gpu_weight_before != gb300_gpu_weight_before  # precond

        client.post("/low-absorb/chain/versions/GB300 NVL72/rollback", json={"target_version": "GB200 NVL72"})

        snap_after = client.get("/low-absorb/chain/snapshot").json()
        gb200_after = next(m for m in snap_after["costModels"] if m["version"] == "GB200 NVL72")
        # Target's components are preserved (NOT overwritten by current_version)
        assert gb200_after["components"][0]["cost_weight"] == gb200_gpu_weight_before
        # Target's status is ACTIVE (or None for backward compat)
        assert gb200_after["status"] is None or gb200_after["status"] == "ACTIVE"

    def test_rollback_version_audit_direction(self) -> None:
        """POST rollback creates audit with before=current, after=target."""
        client = _client()
        client.post("/low-absorb/chain/versions/GB300 NVL72/rollback", json={"target_version": "GB200 NVL72"})

        resp = client.get("/low-absorb/chain/audit")
        assert resp.status_code == 200
        entries = resp.json()
        rollback_entries = [e for e in entries if e["action"] == "rolled_back"]
        assert len(rollback_entries) >= 1
        entry = rollback_entries[0]
        assert entry["before_version"] == "GB300 NVL72"
        assert entry["after_version"] == "GB200 NVL72"

    def test_rollback_same_version_raises(self) -> None:
        client = _client()
        resp = client.post("/low-absorb/chain/versions/GB300 NVL72/rollback", json={"target_version": "GB300 NVL72"})
        assert resp.status_code == 400

    def test_rollback_nonexistent_target_raises(self) -> None:
        client = _client()
        resp = client.post("/low-absorb/chain/versions/GB300 NVL72/rollback", json={"target_version": "NONEXISTENT"})
        assert resp.status_code == 400

    def test_get_audit_log(self) -> None:
        client = _client()
        create_resp = client.post(
            "/low-absorb/chain/updates",
            json={
                "version": "GB300 NVL72",
                "source_type": "manual",
                "source_name": "手动维护",
                "confidence": "high",
                "components": [_sample_component()],
            },
        )
        candidate_id = create_resp.json()["candidate_id"]
        client.post(f"/low-absorb/chain/updates/{candidate_id}/approve")
        resp = client.get("/low-absorb/chain/audit")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 2  # created + approved
