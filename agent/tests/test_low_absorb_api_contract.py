from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.api import register_low_absorb_routes


def _client() -> TestClient:
    app = FastAPI()
    register_low_absorb_routes(app)
    return TestClient(app)


def test_low_absorb_router_exposes_snapshot_contract() -> None:
    client = _client()

    response = client.get("/low-absorb/snapshot")

    assert response.status_code == 200
    body = response.json()
    assert set(body).issuperset({"signals", "trade_plans", "positions", "risk_matrix"})


def test_settings_response_masks_webhook(monkeypatch) -> None:
    monkeypatch.setenv("LOW_ABSORB_FEISHU_WEBHOOK", "https://open.feishu.cn/open-apis/bot/v2/hook/secret-token")
    client = _client()

    response = client.get("/low-absorb/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["maskedWebhook"] == "https://open.feishu.cn/open-apis/bot/v2/hook/****"
    assert "secret-token" not in str(body)


def test_low_absorb_contract_placeholder_endpoints() -> None:
    client = _client()

    assert client.get("/low-absorb/sentiment/snapshot").status_code == 200
    assert client.get("/low-absorb/chain/snapshot").status_code == 200
    assert client.get("/low-absorb/backtest/summary").status_code == 200

    run_response = client.post("/low-absorb/backtest/run")
    assert run_response.status_code == 200
    assert run_response.json()["status"] == "USE_POST_RUNS"


def test_notify_test_handles_missing_webhook_gracefully(monkeypatch) -> None:
    monkeypatch.delenv("LOW_ABSORB_FEISHU_WEBHOOK", raising=False)
    client = _client()

    response = client.post("/low-absorb/notify/test")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error"] == "missing webhook"


def test_data_sources_status_returns_health() -> None:
    client = _client()
    response = client.get("/low-absorb/data-sources/status")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "sources" in body["data"]
    assert "summary" in body["data"]
    assert body["data"]["summary"]["total_sources"] >= 1


def test_data_sources_check_returns_checked_at() -> None:
    client = _client()
    response = client.post("/low-absorb/data-sources/check")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "checked_at" in body["data"]


def test_data_sources_attempts_returns_list() -> None:
    client = _client()
    response = client.get("/low-absorb/data-sources/attempts")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"]["attempts"], list)


def test_health_liveness_contract() -> None:
    """GET /low-absorb/health/liveness must return {'status': 'alive'}."""
    client = _client()
    response = client.get("/low-absorb/health/liveness")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_readiness_contract() -> None:
    """GET /low-absorb/health/readiness must return {ready, failures} with each failure having name/ok/detail."""
    client = _client()
    response = client.get("/low-absorb/health/readiness")
    assert response.status_code == 200
    body = response.json()
    assert "ready" in body
    assert isinstance(body["ready"], bool)
    assert "failures" in body
    assert isinstance(body["failures"], list)
    for f in body["failures"]:
        assert "name" in f
        assert "ok" in f
        assert isinstance(f["ok"], bool)
        assert "detail" in f


def test_health_readiness_detail_is_fixed_summary() -> None:
    """Readiness failure details must be fixed category strings — no paths, keys, tokens, or webhooks."""
    client = _client()
    response = client.get("/low-absorb/health/readiness")
    assert response.status_code == 200
    body = response.json()
    allowed_details = {
        "ok", "configured", "missing",
        "storage_not_writable", "fixture_fallback_forbidden",
        "no_active_version", "fixture_only", "fixture_only_with_production_mode",
    }
    for f in body["failures"]:
        # Details for failed checks must be one of the allowed set
        if not f["ok"]:
            assert f["detail"] in allowed_details, (
                f"Readiness failure '{f['name']}' has unexpected detail '{f['detail']}'"
            )
            # Verify no sensitive data
            assert "/" not in f["detail"], f"Readiness detail contains path: {f['detail']}"
            assert "http" not in f["detail"].lower(), f"Readiness detail contains URL: {f['detail']}"
