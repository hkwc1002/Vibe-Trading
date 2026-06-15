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
    assert run_response.json()["status"] == "BACKTEST_ENGINE_NOT_CONNECTED"


def test_notify_test_handles_missing_webhook_gracefully(monkeypatch) -> None:
    monkeypatch.delenv("LOW_ABSORB_FEISHU_WEBHOOK", raising=False)
    client = _client()

    response = client.post("/low-absorb/notify/test")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error"] == "missing webhook"
