"""E2E workflow tests for the Low Absorb manual-execution flow."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.api import register_low_absorb_routes
from src.low_absorb.api.workbench import reset_workbench_state, set_workbench_storage
from src.low_absorb.data_provider import (
    ChainBranchStrength,
    DailyBar,
    FixtureMarketDataProvider,
    IntradayBar,
    MarketBreadth,
)
from src.low_absorb.storage import InMemoryLowAbsorbStorage

TRADE_DATE = date(2026, 6, 12)
SCAN_AT = datetime(2026, 6, 12, 14, 45)


def _client() -> TestClient:
    app = FastAPI()
    register_low_absorb_routes(app)
    return TestClient(app)


def _daily_bars(symbol: str = "601138") -> list[DailyBar]:
    """Daily bars that trigger a scan signal (MA20 deviation ~0.6%, volume ratio < 0.65)."""
    bars: list[DailyBar] = []
    start_date = date(2026, 5, 18)
    for idx in range(19):
        bars.append(
            DailyBar(
                symbol=symbol,
                trade_date=start_date + timedelta(days=idx),
                open=Decimal("20.00"),
                high=Decimal("20.30"),
                low=Decimal("19.80"),
                close=Decimal("20.00"),
                volume=Decimal("1000000"),
                atr=Decimal("1.00"),
                industry="AI 服务器",
                stock_name="工业富联",
                captured_at=SCAN_AT,
            )
        )
    bars.append(
        DailyBar(
            symbol=symbol,
            trade_date=TRADE_DATE,
            open=Decimal("20.30"),
            high=Decimal("20.55"),
            low=Decimal("19.50"),
            close=Decimal("20.12"),
            volume=Decimal("600000"),
            atr=Decimal("1.00"),
            industry="AI 服务器",
            stock_name="工业富联",
            captured_at=SCAN_AT,
        )
    )
    return bars


def _provider() -> FixtureMarketDataProvider:
    """Fixture provider that produces deterministic scan results."""
    return FixtureMarketDataProvider(
        symbols=["601138"],
        market_breadth=MarketBreadth(
            trade_date=TRADE_DATE,
            captured_at=SCAN_AT,
            total_market_turnover_cny=Decimal("600000000000"),
            limit_break_rate=Decimal("0.20"),
        ),
        daily_bars={"601138": _daily_bars()},
        intraday_bars={
            "601138": [
                IntradayBar(
                    symbol="601138",
                    trade_date=TRADE_DATE,
                    at=SCAN_AT,
                    open=Decimal("19.95"),
                    high=Decimal("20.10"),
                    low=Decimal("19.72"),
                    close=Decimal("20.02"),
                    volume=Decimal("120000"),
                )
            ]
        },
        chain_strength=[
            ChainBranchStrength(
                branch_name="AI 服务器",
                rank=1,
                total_branches=3,
                slope=Decimal("0.08"),
                relative_strength=Decimal("1.20"),
            )
        ],
    )


def setup_function() -> None:
    set_workbench_storage(InMemoryLowAbsorbStorage())
    reset_workbench_state()


def test_workflow_scan_tail_produces_signals_and_plans() -> None:
    """Scan-tail returns signals and trade plans with metadata.

    Covers R1 (scan-tail endpoint), R5 (signal generation + trade plan).
    """
    set_workbench_storage(InMemoryLowAbsorbStorage(), data_provider=_provider())
    client = _client()

    response = client.post(
        "/low-absorb/scan-tail",
        json={"trade_date": TRADE_DATE.isoformat(), "at": SCAN_AT.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["signals"]) > 0
    assert len(body["trade_plans"]) > 0
    assert body["data_source"] == "fixture"

    signal = body["signals"][0]
    plan = body["trade_plans"][0]
    assert "signal_id" in signal
    assert "plan_id" in plan
    assert plan["signal_id"] == signal["signal_id"]


def test_workflow_feishu_handles_missing_webhook_gracefully() -> None:
    """Feishu push gracefully fails when no webhook is configured.

    Covers T8 (notification resilience without real webhook).
    """
    set_workbench_storage(InMemoryLowAbsorbStorage(), data_provider=_provider())
    client = _client()

    # First scan to generate a plan
    scan_resp = client.post(
        "/low-absorb/scan-tail",
        json={"trade_date": TRADE_DATE.isoformat(), "at": SCAN_AT.isoformat()},
    )
    assert scan_resp.status_code == 200
    plan_id = scan_resp.json()["trade_plans"][0]["plan_id"]

    # Push to feishu without webhook configured
    feishu_resp = client.post(f"/low-absorb/trade-plans/{plan_id}/feishu")
    assert feishu_resp.status_code == 200
    data = feishu_resp.json()
    assert data["ok"] is False
    assert data["error"] == "missing webhook"


def test_workflow_manual_fill_creates_position() -> None:
    """Recording a manual fill creates a position and updates plan status.

    Covers T6/T7 (manual fill recording, position creation).
    """
    set_workbench_storage(InMemoryLowAbsorbStorage(), data_provider=_provider())
    client = _client()

    # Scan to generate a plan
    scan_resp = client.post(
        "/low-absorb/scan-tail",
        json={"trade_date": TRADE_DATE.isoformat(), "at": SCAN_AT.isoformat()},
    )
    assert scan_resp.status_code == 200
    plan = scan_resp.json()["trade_plans"][0]
    signal = scan_resp.json()["signals"][0]

    # Record manual fill
    fill_resp = client.post(
        "/low-absorb/fills",
        json={
            "fill_id": "e2e-fill-601138",
            "plan_id": plan["plan_id"],
            "signal_id": signal["signal_id"],
            "stock_code": plan["stock_code"],
            "stock_name": plan["stock_name"],
            "side": "BUY",
            "actual_price": plan["entry_low"],
            "quantity": 1000,
            "fee": "5.00",
            "executed_at": datetime(2026, 6, 12, 14, 55).isoformat(),
            "execution_note": "E2E test manual fill",
        },
    )
    assert fill_resp.status_code == 200
    fill_body = fill_resp.json()
    assert "position" in fill_body
    assert fill_body["position"]["stock_code"] == plan["stock_code"]
    assert fill_body["position"]["status"] == "ACTIVE_POSITION"

    # Check position appears in positions list
    positions_resp = client.get("/low-absorb/positions")
    assert positions_resp.status_code == 200
    positions = positions_resp.json()
    assert len(positions) > 0
    assert positions[0]["position_id"] == fill_body["position"]["position_id"]

    # Check plan status updated
    workbench_resp = client.get("/low-absorb/workbench")
    assert workbench_resp.status_code == 200
    updated_plan = workbench_resp.json()["trade_plans"][0]
    assert updated_plan["status"] == "MANUAL_FILLED"


def test_workflow_supervision_returns_position_status() -> None:
    """Supervision endpoint returns risk supervision status for a position.

    Covers T8 (position supervision).
    """
    set_workbench_storage(InMemoryLowAbsorbStorage(), data_provider=_provider())
    client = _client()

    # Scan + fill to create a position
    scan_resp = client.post(
        "/low-absorb/scan-tail",
        json={"trade_date": TRADE_DATE.isoformat(), "at": SCAN_AT.isoformat()},
    )
    plan = scan_resp.json()["trade_plans"][0]
    signal = scan_resp.json()["signals"][0]

    fill_resp = client.post(
        "/low-absorb/fills",
        json={
            "fill_id": "e2e-fill-supervise",
            "plan_id": plan["plan_id"],
            "signal_id": signal["signal_id"],
            "stock_code": plan["stock_code"],
            "stock_name": plan["stock_name"],
            "side": "BUY",
            "actual_price": plan["entry_low"],
            "quantity": 1000,
            "fee": "5.00",
            "executed_at": datetime(2026, 6, 12, 14, 55).isoformat(),
        },
    )
    position_id = fill_resp.json()["position"]["position_id"]

    # Supervise with current price below stop loss → EXIT_SUGGESTED
    supervise_resp = client.post(
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
    assert supervise_resp.status_code == 200
    supervise_body = supervise_resp.json()
    assert "result" in supervise_body
    assert supervise_body["result"]["status"] in (
        "EXIT_SUGGESTED",
        "HOLD_NOISE",
        "HOLD_WITH_WARNING",
    )


def test_workflow_close_report_generated_and_listed() -> None:
    """Close report is generated and appears in the reports list.

    Covers T10 (report generation, archiving).
    """
    set_workbench_storage(InMemoryLowAbsorbStorage(), data_provider=_provider())
    client = _client()

    # Scan + fill for position data in report
    scan_resp = client.post(
        "/low-absorb/scan-tail",
        json={"trade_date": TRADE_DATE.isoformat(), "at": SCAN_AT.isoformat()},
    )
    plan = scan_resp.json()["trade_plans"][0]
    signal = scan_resp.json()["signals"][0]
    client.post(
        "/low-absorb/fills",
        json={
            "fill_id": "e2e-fill-report",
            "plan_id": plan["plan_id"],
            "signal_id": signal["signal_id"],
            "stock_code": plan["stock_code"],
            "stock_name": plan["stock_name"],
            "side": "BUY",
            "actual_price": plan["entry_low"],
            "quantity": 1000,
            "fee": "5.00",
            "executed_at": datetime(2026, 6, 12, 14, 55).isoformat(),
        },
    )

    # Generate close report
    report_resp = client.post(
        "/low-absorb/reports/close",
        params={"trade_date": TRADE_DATE.isoformat()},
    )
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert "report_id" in report
    assert report["trade_date"] == TRADE_DATE.isoformat()

    # Reports list is non-empty
    list_resp = client.get("/low-absorb/reports")
    assert list_resp.status_code == 200
    reports = list_resp.json()
    assert len(reports["reports"]) > 0
    assert reports["reports"][0]["report_id"] == report["report_id"]


def test_workflow_position_close_marks_as_manual_exited() -> None:
    """Closing a position via the API marks it as MANUAL_EXITED with timestamp.

    Covers T7 (position close).
    """
    set_workbench_storage(InMemoryLowAbsorbStorage(), data_provider=_provider())
    client = _client()

    # Scan + fill
    scan_resp = client.post(
        "/low-absorb/scan-tail",
        json={"trade_date": TRADE_DATE.isoformat(), "at": SCAN_AT.isoformat()},
    )
    plan = scan_resp.json()["trade_plans"][0]
    signal = scan_resp.json()["signals"][0]

    fill_resp = client.post(
        "/low-absorb/fills",
        json={
            "fill_id": "e2e-fill-close-test",
            "plan_id": plan["plan_id"],
            "signal_id": signal["signal_id"],
            "stock_code": plan["stock_code"],
            "stock_name": plan["stock_name"],
            "side": "BUY",
            "actual_price": plan["entry_low"],
            "quantity": 1000,
            "fee": "5.00",
            "executed_at": datetime(2026, 6, 12, 14, 55).isoformat(),
        },
    )
    position_id = fill_resp.json()["position"]["position_id"]

    # Close the position
    closed_resp = client.post(
        f"/low-absorb/positions/{position_id}/close",
        json={
            "closed_at": datetime(2026, 6, 13, 10, 5).isoformat(),
            "note": "E2E test manual close",
        },
    )
    assert closed_resp.status_code == 200
    assert closed_resp.json()["status"] == "MANUAL_EXITED"
    assert closed_resp.json()["closed_at"] is not None
