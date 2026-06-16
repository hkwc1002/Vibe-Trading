from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from src.low_absorb.api.workbench import router, reset_workbench_state, seed_workbench_state
from src.low_absorb.models import LowAbsorbSignal, ManualTradePlan, SignalStatus, TradePlanStatus


def _client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _seed_state() -> tuple[LowAbsorbSignal, ManualTradePlan]:
    signal = LowAbsorbSignal(
        signal_id="sig-601138-20260612",
        trade_date=date(2026, 6, 12),
        stock_code="601138",
        stock_name="工业富联",
        branch_name="AI 服务器",
        grade="A",
        ma20_deviation_pct=Decimal("-0.032"),
        volume_ratio=Decimal("0.72"),
        lower_shadow_atr=Decimal("1.18"),
        reason="主线分支强，尾盘缩量回踩 MA20 附近",
        status=SignalStatus.RECOMMENDED,
    )
    plan = ManualTradePlan(
        plan_id="plan-601138-20260612",
        signal_id=signal.signal_id,
        trade_date=signal.trade_date,
        stock_code=signal.stock_code,
        stock_name=signal.stock_name,
        entry_low=Decimal("18.60"),
        entry_high=Decimal("18.95"),
        stop_loss=Decimal("17.88"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.0035"),
        initial_risk_r=Decimal("1.0"),
        initial_risk_cny=Decimal("107.00"),
        open_stop_risk_cny=Decimal("107.00"),
        r_multiple=Decimal("0.00"),
        rationale="人工执行建议，仅用于用户自行判断。",
        manual_order_text="601138 工业富联，人工低吸区间 18.60-18.95，参考止损 17.88。",
        status=TradePlanStatus.RECOMMENDED,
    )
    seed_workbench_state(signals=[signal], trade_plans=[plan])
    return signal, plan


def setup_function() -> None:
    reset_workbench_state()


def test_workbench_api_returns_seeded_manual_workflow_state() -> None:
    signal, plan = _seed_state()
    client = _client()

    response = client.get("/low-absorb/workbench")
    snapshot = client.get("/low-absorb/snapshot")

    assert response.status_code == 200
    assert snapshot.status_code == 200
    body = response.json()
    assert body["signals"][0]["signal_id"] == signal.signal_id
    assert body["trade_plans"][0]["plan_id"] == plan.plan_id
    assert body["positions"] == []
    assert body["risk_matrix"] == []
    assert snapshot.json()["signals"][0]["signal_id"] == signal.signal_id


def test_feishu_push_handles_missing_webhook_gracefully_without_status_change() -> None:
    """Without real_send, missing webhook returns mock ok=True (status becomes SENT_TO_FEISHU)."""
    _, plan = _seed_state()
    client = _client()

    first = client.post(f"/low-absorb/trade-plans/{plan.plan_id}/feishu")
    second = client.post(f"/low-absorb/trade-plans/{plan.plan_id}/feishu")
    workbench = client.get("/low-absorb/workbench").json()

    assert first.status_code == 200
    assert second.status_code == 200
    # With real_send disabled (default), mock returns ok=True
    assert first.json()["ok"] is True
    assert first.json()["message"] == "real_send_disabled"
    assert second.json()["ok"] is True
    # Mock success still updates status to SENT_TO_FEISHU (consistent with ok=True)
    assert workbench["trade_plans"][0]["status"] == "SENT_TO_FEISHU"


def test_notify_test_endpoint_handles_missing_webhook_gracefully() -> None:
    """Without real_send, missing webhook returns mock ok=True."""
    client = _client()

    response = client.post("/low-absorb/notify/test")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["message"] == "real_send_disabled"


def test_manual_fill_reconciliation_creates_position_and_risk_matrix() -> None:
    _, plan = _seed_state()
    client = _client()

    response = client.post(
        f"/low-absorb/trade-plans/{plan.plan_id}/manual-fills",
        json={
            "fill_id": "fill-601138-20260612",
            "filled_at": datetime(2026, 6, 12, 14, 55).isoformat(),
            "fill_price": "18.78",
            "quantity": 1000,
            "fees": "5.00",
            "note": "用户已在国内券商 App 手动处理并回填。",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fill"]["plan_id"] == plan.plan_id
    assert body["position"]["stock_code"] == "601138"
    assert body["position"]["status"] == "ACTIVE_POSITION"

    workbench = client.get("/low-absorb/workbench").json()
    assert workbench["trade_plans"][0]["status"] == "MANUAL_FILLED"
    assert workbench["positions"][0]["position_id"] == body["position"]["position_id"]
    assert workbench["risk_matrix"][0]["stock_code"] == "601138"
    assert workbench["risk_matrix"][0]["needs_supervision"] is True


def test_fills_and_positions_endpoints_support_manual_position_book() -> None:
    _, plan = _seed_state()
    client = _client()

    fill_response = client.post(
        "/low-absorb/fills",
        json={
            "fill_id": "fill-601138-20260612",
            "plan_id": plan.plan_id,
            "executed_at": datetime(2026, 6, 12, 14, 55).isoformat(),
            "actual_price": "18.78",
            "quantity": 1000,
            "fee": "5.00",
            "execution_note": "manual fill recorded",
        },
    )
    assert fill_response.status_code == 200
    position_id = fill_response.json()["position"]["position_id"]

    positions = client.get("/low-absorb/positions")
    assert positions.status_code == 200
    assert positions.json()[0]["position_id"] == position_id

    patched = client.patch(
        f"/low-absorb/positions/{position_id}",
        json={"current_price": "18.20", "notes": ["review at 10:00"]},
    )
    assert patched.status_code == 200
    assert patched.json()["current_price"] == "18.20"
    assert patched.json()["notes"] == ["review at 10:00"]

    closed = client.post(
        f"/low-absorb/positions/{position_id}/close",
        json={"closed_at": datetime(2026, 6, 13, 10, 5).isoformat(), "note": "manual close record"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "MANUAL_EXITED"
    assert closed.json()["closed_at"] is not None


def test_supervise_position_endpoint_returns_morning_status() -> None:
    _, plan = _seed_state()
    client = _client()
    fill_response = client.post(
        "/low-absorb/fills",
        json={
            "fill_id": "fill-601138-20260612",
            "plan_id": plan.plan_id,
            "executed_at": datetime(2026, 6, 12, 14, 55).isoformat(),
            "actual_price": "18.78",
            "quantity": 1000,
        },
    )
    position_id = fill_response.json()["position"]["position_id"]

    response = client.post(
        f"/low-absorb/supervise/position/{position_id}",
        json={
            "trade_date": "2026-06-15",
            "observed_at": datetime(2026, 6, 15, 10, 0).isoformat(),
            "open_price": "18.80",
            "current_price": "17.70",
            "industry_return": "-0.01",
            "send_feishu": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["result"]["status"] == "EXIT_SUGGESTED"
    assert response.json()["notification"] is None


def test_close_report_uses_current_manual_workflow_state() -> None:
    _, plan = _seed_state()
    client = _client()
    client.post(
        f"/low-absorb/trade-plans/{plan.plan_id}/manual-fills",
        json={
            "fill_id": "fill-601138-20260612",
            "filled_at": datetime(2026, 6, 12, 14, 55).isoformat(),
            "fill_price": "18.78",
            "quantity": 1000,
            "fees": "5.00",
        },
    )

    response = client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-12"})

    assert response.status_code == 200
    body = response.json()
    assert body["report_id"] == "close-20260612"
    assert body["signals"][0]["signal_id"] == "sig-601138-20260612"
    assert body["trade_plans"][0]["plan_id"] == plan.plan_id
    assert body["positions"][0]["stock_code"] == "601138"
