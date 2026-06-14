from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.api import register_low_absorb_routes
from src.low_absorb.api.workbench import reset_workbench_state, set_workbench_storage
from src.low_absorb.config import LowAbsorbConfig
from src.low_absorb.data_provider import ChainBranchStrength, DailyBar, FixtureMarketDataProvider, IntradayBar, MarketBreadth
from src.low_absorb.models import ManualPosition, RiskSupervisionStatus
from src.low_absorb.notifier import FeishuNotifier, build_notifier_test_card
from src.low_absorb.storage import InMemoryLowAbsorbStorage, JsonLowAbsorbStorage
from src.low_absorb.supervisor import supervise_position_morning


TRADE_DATE = date(2026, 6, 12)
SCAN_AT = datetime(2026, 6, 12, 14, 45)


def _client() -> TestClient:
    app = FastAPI()
    register_low_absorb_routes(app)
    return TestClient(app)


def _daily_bars(symbol: str = "601138") -> list[DailyBar]:
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


def _position() -> ManualPosition:
    return ManualPosition(
        position_id="pos-601138-20260612",
        plan_id="plan-601138-20260612",
        stock_code="601138",
        stock_name="工业富联",
        branch="AI 服务器",
        opened_at=datetime(2026, 6, 12, 14, 55),
        avg_cost=Decimal("20.00"),
        current_price=Decimal("20.00"),
        initial_stop_price=Decimal("19.80"),
        current_stop_price=Decimal("19.80"),
        quantity=1000,
        position_weight=Decimal("0.12"),
    )


def setup_function() -> None:
    set_workbench_storage(InMemoryLowAbsorbStorage())
    reset_workbench_state()


def test_default_strategy_thresholds_match_p0_spec() -> None:
    config = LowAbsorbConfig()

    assert config.min_market_turnover_cny == Decimal("500000000000")
    assert config.max_limit_break_rate == Decimal("0.45")
    assert config.ma20_deviation_min == Decimal("0")
    assert config.ma20_deviation_max == Decimal("0.012")
    assert config.max_volume_ratio_5d == Decimal("0.65")
    assert config.min_lower_shadow_atr == Decimal("0.5")


def test_scan_tail_endpoint_runs_scanner_and_persists_results(tmp_path) -> None:
    storage = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    set_workbench_storage(storage, data_provider=_provider())
    client = _client()

    response = client.post(
        "/low-absorb/scan-tail",
        json={"trade_date": "2026-06-12", "at": SCAN_AT.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["signals"][0]["signal_id"] == "sig-601138-20260612"
    assert body["trade_plans"][0]["plan_id"] == "plan-601138-20260612"
    assert body["data_source"] == "fixture"

    reloaded = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    assert "sig-601138-20260612" in reloaded.signals
    assert "plan-601138-20260612" in reloaded.trade_plans


def test_scan_tail_returns_blocked_signals_when_budget_exceeded() -> None:
    """API returns blocked_signals when portfolio risk budget is exceeded."""
    symbols = ["600089", "601138", "603019", "605333", "603912", "603986"]
    daily_bars: dict[str, list[DailyBar]] = {}
    intraday_bars_dict: dict[str, list[IntradayBar]] = {}
    for sym in symbols:
        daily_bars[sym] = _daily_bars(sym)
        intraday_bars_dict[sym] = [
            IntradayBar(
                symbol=sym, trade_date=TRADE_DATE, at=SCAN_AT,
                open=Decimal("19.95"), high=Decimal("20.10"),
                low=Decimal("19.72"), close=Decimal("20.02"),
                volume=Decimal("120000"),
            )
        ]

    provider = FixtureMarketDataProvider(
        symbols=symbols,
        market_breadth=MarketBreadth(
            trade_date=TRADE_DATE, captured_at=SCAN_AT,
            total_market_turnover_cny=Decimal("900000000000"),
            limit_break_rate=Decimal("0.20"),
        ),
        daily_bars=daily_bars,
        intraday_bars=intraday_bars_dict,
        chain_strength=[
            ChainBranchStrength(
                branch_name="AI 服务器", rank=1, total_branches=3,
                slope=Decimal("0.08"), relative_strength=Decimal("1.20"),
            ),
        ],
    )

    storage = InMemoryLowAbsorbStorage()
    storage.update_config({
        "min_market_turnover_cny": "800000000000",
        "max_limit_break_rate": "0.50",
        "ma20_deviation_min": "-0.05",
        "ma20_deviation_max": "0.01",
        "max_volume_ratio_5d": "0.85",
        "min_lower_shadow_atr": "0.5",
        "max_data_staleness_seconds": 60,
        "max_single_position_weight": "0.12",
        "max_single_trade_risk_pct": "0.0035",
    })
    set_workbench_storage(storage, data_provider=provider)
    client = _client()

    response = client.post(
        "/low-absorb/scan-tail",
        json={"trade_date": "2026-06-12", "at": SCAN_AT.isoformat(), "symbols": symbols},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["signals"]) == 5
    assert len(body["blocked_signals"]) == 1
    blocked = body["blocked_signals"][0]
    assert blocked["block_reason"] != ""
    assert "风险预算" in blocked["block_reason"]
    blocked_ids = {s["signal_id"] for s in body["blocked_signals"]}
    plan_signal_ids = {p["signal_id"] for p in body["trade_plans"]}
    assert blocked_ids.isdisjoint(plan_signal_ids)


def test_reports_api_uses_persistent_storage(tmp_path) -> None:
    storage = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    set_workbench_storage(storage, data_provider=_provider())
    client = _client()
    client.post("/low-absorb/scan-tail", json={"trade_date": "2026-06-12", "at": SCAN_AT.isoformat()})

    created = client.post("/low-absorb/reports/close", params={"trade_date": "2026-06-12"})
    listed = client.get("/low-absorb/reports")

    assert created.status_code == 200
    assert listed.status_code == 200
    assert listed.json()["reports"][0]["report_id"] == "close-20260612"
    assert "close-20260612" in JsonLowAbsorbStorage(tmp_path / "low_absorb.json").reports


def test_settings_update_persists_and_never_returns_full_webhook(tmp_path) -> None:
    storage = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    set_workbench_storage(storage)
    client = _client()

    response = client.patch(
        "/low-absorb/settings",
        json={
            "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/secret-token",
            "config": {"max_limit_break_rate": "0.33"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["maskedWebhook"] == "https://open.feishu.cn/open-apis/bot/v2/hook/****"
    assert body["webhookConfigured"] is True
    assert body["config"]["max_limit_break_rate"] == "0.33"
    assert "secret-token" not in str(body)

    reloaded = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    assert reloaded.get_webhook() == "https://open.feishu.cn/open-apis/bot/v2/hook/secret-token"
    assert reloaded.get_config().max_limit_break_rate == Decimal("0.33")


def test_supervisor_uses_first_0930_1000_bar_even_when_later_bars_exist() -> None:
    provider = FixtureMarketDataProvider(
        intraday_bars={
            "601138": [
                IntradayBar(
                    symbol="601138",
                    trade_date=date(2026, 6, 15),
                    at=datetime(2026, 6, 15, 10, 0),
                    open=Decimal("20.00"),
                    high=Decimal("20.10"),
                    low=Decimal("19.70"),
                    close=Decimal("19.90"),
                    volume=Decimal("100000"),
                ),
                IntradayBar(
                    symbol="601138",
                    trade_date=date(2026, 6, 15),
                    at=datetime(2026, 6, 15, 10, 30),
                    open=Decimal("19.90"),
                    high=Decimal("20.00"),
                    low=Decimal("18.80"),
                    close=Decimal("18.90"),
                    volume=Decimal("300000"),
                ),
            ]
        }
    )

    result = supervise_position_morning(
        position=_position(),
        provider=provider,
        trade_date=date(2026, 6, 15),
        observed_at=datetime(2026, 6, 15, 10, 0),
    )

    assert result.first_30m_close == Decimal("19.90")
    assert result.status is RiskSupervisionStatus.HOLD_NOISE


def test_feishu_card_builders_emit_interactive_schema() -> None:
    test_card = build_notifier_test_card()
    assert test_card["msg_type"] == "interactive"
    assert "card" in test_card
    assert "header" in test_card["card"]
    assert "elements" in test_card["card"]


@pytest.mark.skipif(not os.getenv("LOW_ABSORB_FEISHU_WEBHOOK"), reason="需要真实飞书 webhook")
def test_real_feishu_webhook_smoke_is_env_guarded() -> None:
    notifier = FeishuNotifier(
        webhook_url=os.environ["LOW_ABSORB_FEISHU_WEBHOOK"],
        storage=InMemoryLowAbsorbStorage(),
    )

    result = notifier.send_test_notification(force=True)

    assert result.ok is True
