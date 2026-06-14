"""Tests for close report generation and API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.api import register_low_absorb_routes
from src.low_absorb.api.workbench import set_workbench_storage
from src.low_absorb.models import (
    LowAbsorbSignal,
    ManualFill,
    ManualPosition,
    ManualTradePlan,
    PositionStatus,
    SignalStatus,
    TradePlanStatus,
)
from src.low_absorb.report import build_close_report
from src.low_absorb.storage import InMemoryLowAbsorbStorage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client() -> TestClient:
    storage = InMemoryLowAbsorbStorage()
    set_workbench_storage(storage)
    app = FastAPI()
    register_low_absorb_routes(app)
    return TestClient(app)


def _make_signal(**overrides: object) -> LowAbsorbSignal:
    base = {
        "signal_id": "sig-601138-20260614",
        "trade_date": date(2026, 6, 14),
        "stock_code": "601138",
        "stock_name": "工业富联",
        "branch_name": "AI 服务器",
        "grade": "A",
        "ma20_deviation_pct": Decimal("-0.032"),
        "volume_ratio": Decimal("0.72"),
        "lower_shadow_atr": Decimal("1.18"),
        "reason": "主线分支强，尾盘缩量回踩 MA20 附近",
    }
    base.update(overrides)
    return LowAbsorbSignal(**base)


def _make_plan(**overrides: object) -> ManualTradePlan:
    base = {
        "plan_id": "plan-601138-20260614",
        "signal_id": "sig-601138-20260614",
        "trade_date": date(2026, 6, 14),
        "stock_code": "601138",
        "stock_name": "工业富联",
        "entry_low": Decimal("18.60"),
        "entry_high": Decimal("18.95"),
        "stop_loss": Decimal("17.88"),
        "planned_position_pct": Decimal("0.12"),
        "max_risk_pct": Decimal("0.0035"),
        "initial_risk_r": Decimal("1.0"),
        "initial_risk_cny": Decimal("107.00"),
        "open_stop_risk_cny": Decimal("107.00"),
        "r_multiple": Decimal("0.00"),
        "rationale": "人工执行建议",
        "manual_order_text": "601138 工业富联，人工低吸区间 18.60-18.95",
        "status": TradePlanStatus.RECOMMENDED,
    }
    base.update(overrides)
    return ManualTradePlan(**base)


def _make_fill(**overrides: object) -> ManualFill:
    base = {
        "fill_id": "fill-601138-20260614",
        "plan_id": "plan-601138-20260614",
        "stock_code": "601138",
        "stock_name": "工业富联",
        "actual_price": Decimal("18.78"),
        "quantity": 1000,
        "fee": Decimal("5.00"),
        "executed_at": datetime(2026, 6, 14, 14, 55),
    }
    base.update(overrides)
    return ManualFill(**base)


def _make_position(**overrides: object) -> ManualPosition:
    base = {
        "position_id": "pos-601138-20260614",
        "plan_id": "plan-601138-20260614",
        "stock_code": "601138",
        "stock_name": "工业富联",
        "opened_at": datetime(2026, 6, 14, 14, 55),
        "avg_cost": Decimal("18.78"),
        "current_price": Decimal("18.80"),
        "stop_loss": Decimal("17.88"),
        "quantity": 1000,
        "position_pct": Decimal("0.12"),
        "status": PositionStatus.ACTIVE_POSITION,
    }
    base.update(overrides)
    return ManualPosition(**base)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReportGeneration:
    """Close report generation and computed review_items."""

    def test_empty_storage_returns_valid_close_report(self) -> None:
        client = _client()
        response = client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-14"})
        assert response.status_code == 200
        body = response.json()
        assert body["report_id"] == "close-20260614"
        assert body["signals"] == []
        assert body["trade_plans"] == []
        assert body["positions"] == []
        assert isinstance(body["review_items"], list)

    def test_report_with_seeded_data_has_correct_counts(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        storage.seed(
            signals=[_make_signal()],
            trade_plans=[_make_plan()],
            fills=[_make_fill()],
            positions=[_make_position()],
        )
        set_workbench_storage(storage)
        app = FastAPI()
        register_low_absorb_routes(app)
        client = TestClient(app)

        response = client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-14"})
        assert response.status_code == 200
        body = response.json()
        assert len(body["signals"]) == 1
        assert len(body["trade_plans"]) == 1
        assert len(body["positions"]) == 1

        review_text = " ".join(body["review_items"])
        assert "待人工成交回填" in review_text
        assert "次日 10:00 需要监督的持仓" in review_text

    def test_report_identifies_invalidated_signals_and_pending_fills(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        storage.seed(
            signals=[
                _make_signal(signal_id="sig-001", status=SignalStatus.INVALIDATED),
                _make_signal(signal_id="sig-002", status=SignalStatus.RECOMMENDED),
            ],
            trade_plans=[
                _make_plan(plan_id="plan-001", status=TradePlanStatus.RECOMMENDED),
                _make_plan(plan_id="plan-002", status=TradePlanStatus.MANUAL_FILLED),
            ],
            positions=[_make_position(position_id="pos-001")],
        )
        set_workbench_storage(storage)
        app = FastAPI()
        register_low_absorb_routes(app)
        client = TestClient(app)

        response = client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-14"})
        assert response.status_code == 200
        body = response.json()

        review_text = " ".join(body["review_items"])
        assert "待人工成交回填" in review_text  # plan-001 is RECOMMENDED (pending)
        assert "失效候选信号" in review_text  # sig-001 is INVALIDATED
        assert "次日" in review_text  # pos-001 is ACTIVE_POSITION

    def test_build_close_report_pure_function(self) -> None:
        signal = _make_signal()
        plan = _make_plan()
        position = _make_position()

        report = build_close_report(
            report_id="close-20260614-test",
            trade_date=date(2026, 6, 14),
            signals=[signal],
            trade_plans=[plan],
            positions=[position],
            review_items=["人工复核"],
        )
        assert report.report_id == "close-20260614-test"
        assert len(report.review_items) > 1  # manual item + computed items


class TestReportsAPI:
    """GET /reports and POST /close endpoints."""

    def test_get_reports_empty_before_generation(self) -> None:
        client = _client()
        response = client.get("/low-absorb/reports")
        assert response.status_code == 200
        assert response.json()["reports"] == []

    def test_get_reports_returns_reports_after_generation(self) -> None:
        client = _client()
        client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-14"})

        response = client.get("/low-absorb/reports")
        assert response.status_code == 200
        body = response.json()
        assert len(body["reports"]) == 1
        assert body["reports"][0]["report_id"] == "close-20260614"

    def test_post_close_stores_report(self) -> None:
        client = _client()
        response = client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-14"})
        assert response.status_code == 200

        stored = client.get("/low-absorb/reports").json()
        assert len(stored["reports"]) == 1

    def test_notify_missing_webhook_gracefully(self) -> None:
        client = _client()
        client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-14"})

        response = client.post("/low-absorb/reports/close/notify")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["error"] == "missing webhook"

    def test_get_reports_filters_by_trade_date(self) -> None:
        client = _client()
        client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-13"})
        client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-14"})

        response = client.get("/low-absorb/reports?trade_date=2026-06-13")
        assert response.status_code == 200
        body = response.json()
        assert len(body["reports"]) == 1
        assert body["reports"][0]["trade_date"] == "2026-06-13"
