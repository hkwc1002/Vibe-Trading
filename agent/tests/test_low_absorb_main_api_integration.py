from __future__ import annotations

from fastapi.testclient import TestClient

import api_server


def test_main_fastapi_app_mounts_low_absorb_routes_with_auth(monkeypatch) -> None:
    monkeypatch.delenv("API_AUTH_KEY", raising=False)
    remote_client = TestClient(api_server.app, client=("203.0.113.10", 50000))

    response = remote_client.get("/low-absorb/snapshot")

    assert response.status_code == 403
    assert response.json()["detail"] == "API_AUTH_KEY is required for non-local API access"


def test_all_low_absorb_routes_mounted() -> None:
    """Verify that all expected Low Absorb routers are registered on the app."""
    routes = [route.path for route in api_server.app.routes]
    expected_prefixes = [
        "/low-absorb/sentiment",
        "/low-absorb/backtest",
        "/low-absorb/chain",
        "/low-absorb/reports",
        "/low-absorb/settings",
        "/low-absorb/workbench",
        "/low-absorb/snapshot",
        "/low-absorb/scan-tail",
        "/low-absorb/fills",
        "/low-absorb/positions",
        "/low-absorb/supervise",
    ]
    for prefix in expected_prefixes:
        matching = [r for r in routes if r.startswith(prefix)]
        assert matching, f"Expected route prefix '{prefix}' not found among registered routes"
