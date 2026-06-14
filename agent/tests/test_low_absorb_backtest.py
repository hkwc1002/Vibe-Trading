"""Tests for the backtest API endpoints."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.api.backtest import build_backtest_snapshot, router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_get_summary_returns_200_with_expected_keys() -> None:
    """GET /summary returns all top-level keys."""
    client = _client()
    response = client.get("/low-absorb/backtest/summary")
    assert response.status_code == 200
    body = response.json()
    expected = {
        "metrics", "parameters", "historicalSignals",
        "sensitivity", "branchAttribution", "suggestions", "message",
    }
    assert set(body).issuperset(expected)


def test_get_runs_returns_empty_list() -> None:
    """GET /low-absorb/backtest returns an empty runs list."""
    client = _client()
    response = client.get("/low-absorb/backtest")
    assert response.status_code == 200
    assert response.json() == {"runs": []}


def test_post_run_returns_expected_structure() -> None:
    """POST /run returns BACKTEST_ENGINE_NOT_CONNECTED."""
    client = _client()
    response = client.post("/low-absorb/backtest/run")
    assert response.status_code == 200
    body = response.json()
    assert body["runId"] is None
    assert body["status"] == "BACKTEST_ENGINE_NOT_CONNECTED"
    assert "message" in body


def test_metrics_contains_all_six_fields() -> None:
    """build_backtest_snapshot metrics list has all 6 entries."""
    snapshot = build_backtest_snapshot()
    metrics = snapshot["metrics"]
    assert isinstance(metrics, list)
    assert len(metrics) == 6
    ids = {m["id"] for m in metrics}
    expected = {"win-rate", "avg-r", "drawdown", "samples", "profit-factor", "best-branch"}
    assert ids == expected


def test_parameters_list_is_non_empty() -> None:
    """Parameters list should contain example parameter entries."""
    snapshot = build_backtest_snapshot()
    assert isinstance(snapshot["parameters"], list)
    assert len(snapshot["parameters"]) > 0


def test_historical_signals_list_is_non_empty() -> None:
    """Historical signals list should contain example signal entries."""
    snapshot = build_backtest_snapshot()
    assert isinstance(snapshot["historicalSignals"], list)
    assert len(snapshot["historicalSignals"]) > 0


def test_branch_attribution_sorts_by_contribution_descending() -> None:
    """Branch attribution rows are sorted by contribution descending."""
    snapshot = build_backtest_snapshot()
    rows = snapshot["branchAttribution"]
    contributions = [int(r["contribution"].rstrip("%")) for r in rows]
    assert contributions == sorted(contributions, reverse=True)


def test_suggestions_is_a_list_of_strings() -> None:
    """Suggestions is a non-empty list of strings."""
    snapshot = build_backtest_snapshot()
    suggestions = snapshot["suggestions"]
    assert isinstance(suggestions, list)
    assert all(isinstance(s, str) for s in suggestions)
    assert len(suggestions) > 0
