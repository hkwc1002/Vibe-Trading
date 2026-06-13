from __future__ import annotations

from fastapi.testclient import TestClient

import api_server


def test_main_fastapi_app_mounts_low_absorb_routes_with_auth(monkeypatch) -> None:
    monkeypatch.delenv("API_AUTH_KEY", raising=False)
    remote_client = TestClient(api_server.app, client=("203.0.113.10", 50000))

    response = remote_client.get("/low-absorb/snapshot")

    assert response.status_code == 403
    assert response.json()["detail"] == "API_AUTH_KEY is required for non-local API access"
