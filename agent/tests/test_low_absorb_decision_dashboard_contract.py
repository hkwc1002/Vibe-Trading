from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.low_absorb.api import register_low_absorb_routes
from src.low_absorb.api.workbench import set_workbench_storage
from src.low_absorb.config import LowAbsorbConfig
from src.low_absorb.data_provider import ChainBranchStrength, DailyBar, FixtureMarketDataProvider, MarketBreadth
from src.low_absorb.scanner import LowAbsorbScanner
from src.low_absorb.storage import InMemoryLowAbsorbStorage, JsonLowAbsorbStorage


SCAN_AT = datetime(2026, 6, 12, 14, 45)


def _client(storage: InMemoryLowAbsorbStorage | JsonLowAbsorbStorage | None = None) -> TestClient:
    set_workbench_storage(storage or InMemoryLowAbsorbStorage())
    app = FastAPI()
    register_low_absorb_routes(app)
    return TestClient(app)


def _bars(symbol: str, stock_name: str, industry: str, close: Decimal = Decimal("20.12")) -> list[DailyBar]:
    start = date(2026, 6, 12) - timedelta(days=25)
    rows = [
        DailyBar(
            symbol=symbol,
            trade_date=start + timedelta(days=idx),
            open=Decimal("20.00"),
            high=Decimal("20.40"),
            low=Decimal("19.80"),
            close=Decimal("20.00"),
            volume=Decimal("1000000"),
            atr=Decimal("1.00"),
            industry=industry,
            stock_name=stock_name,
            captured_at=SCAN_AT,
        )
        for idx in range(19)
    ]
    rows.append(
        DailyBar(
            symbol=symbol,
            trade_date=date(2026, 6, 12),
            open=Decimal("20.30"),
            high=Decimal("20.55"),
            low=Decimal("19.50"),
            close=close,
            volume=Decimal("600000"),
            atr=Decimal("1.00"),
            industry=industry,
            stock_name=stock_name,
            captured_at=SCAN_AT,
        )
    )
    return rows


def test_cost_chain_models_roundtrip_in_json_storage(tmp_path) -> None:
    storage = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")

    models = storage.get_cost_chain_models()

    assert {"GB200 NVL72", "GB300 NVL72", "custom/manual"}.issubset(models)
    manual = models["custom/manual"]
    first = manual.components[0].model_copy(update={"cost_weight": Decimal("0.19"), "signal_weight": Decimal("0.88")})
    storage.update_cost_chain_model("custom/manual", [first, *manual.components[1:]])

    reloaded = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    updated = reloaded.get_cost_chain_models()["custom/manual"].components[0]
    assert updated.cost_weight == Decimal("0.19")
    assert updated.signal_weight == Decimal("0.88")


def test_chain_snapshot_returns_cost_workspace_contract() -> None:
    client = _client()

    response = client.get("/low-absorb/chain/snapshot")

    assert response.status_code == 200
    body = response.json()
    assert body["activeVersion"] == "GB300 NVL72"
    assert {"成本总览", "GPU/加速卡", "HBM/存储", "CPO/光模块", "PCB/高速板", "服务器ODM", "液冷散热", "电源连接器"}.issubset(
        {tab["label"] for tab in body["sectorTabs"]}
    )
    assert {
        "component",
        "cost_weight",
        "cost_weight_range",
        "cost_increase_vs_previous_generation",
        "signal_weight",
        "source_type",
        "source_url",
        "confidence",
        "is_estimated",
        "methodology_note",
    }.issubset(body["costTable"][0])
    assert body["costTable"][0]["source_url"].startswith("https://")
    assert body["costTable"][0]["confidence"] in {"high", "medium", "low"}
    assert len(body["sectors"][0]["stocks"]) <= 5
    assert {"leader", "core_middle_cap", "sentiment_stock", "mainboard_mapping", "watch_only"}.issubset(
        {stock["role"] for sector in body["sectors"] for stock in sector["stocks"]}
    )


def test_custom_cost_chain_model_can_be_edited_from_chain_api(tmp_path) -> None:
    storage = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    client = _client(storage)
    component = storage.get_cost_chain_models()["custom/manual"].components[0].model_copy(
        update={"cost_weight": Decimal("0.21"), "signal_weight": Decimal("0.77")}
    )

    response = client.patch(
        "/low-absorb/chain/cost-models/custom/manual",
        json={"components": [component.model_dump(mode="json")]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "custom/manual"
    assert body["components"][0]["cost_weight"] == "0.21"
    reloaded = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    assert reloaded.get_cost_chain_models()["custom/manual"].components[0].signal_weight == Decimal("0.77")


def test_builtin_cost_chain_model_cannot_be_edited_from_chain_api(tmp_path) -> None:
    storage = JsonLowAbsorbStorage(tmp_path / "low_absorb.json")
    client = _client(storage)
    component = storage.get_cost_chain_models()["GB300 NVL72"].components[0]

    response = client.patch(
        "/low-absorb/chain/cost-models/GB300 NVL72",
        json={"components": [component.model_dump(mode="json")]},
    )

    assert response.status_code == 400
    assert "custom/manual" in response.json()["detail"]


def test_scan_tail_ranks_candidates_with_chain_strength_and_cost_weight() -> None:
    trade_date = date(2026, 6, 12)
    provider = FixtureMarketDataProvider(
        symbols=["601138", "600089"],
        market_breadth=MarketBreadth(
            trade_date=trade_date,
            captured_at=SCAN_AT,
            total_market_turnover_cny=Decimal("600000000000"),
            limit_break_rate=Decimal("0.20"),
        ),
        daily_bars={
            "601138": _bars("601138", "工业富联", "服务器ODM"),
            "600089": _bars("600089", "特变电工", "电源连接器"),
        },
        chain_strength=[
            ChainBranchStrength(
                branch_name="服务器ODM",
                rank=2,
                total_branches=2,
                slope=Decimal("0.01"),
                relative_strength=Decimal("1.05"),
            ),
            ChainBranchStrength(
                branch_name="电源连接器",
                rank=1,
                total_branches=2,
                slope=Decimal("0.08"),
                relative_strength=Decimal("1.25"),
            ),
        ],
    )
    config = LowAbsorbConfig(
        chain_cost_signal_weights={"服务器ODM": Decimal("0.30"), "电源连接器": Decimal("0.95")}
    )

    result = LowAbsorbScanner(provider, config).scan_tail_session_with_signals(trade_date, at=SCAN_AT)

    assert [plan.stock_code for plan in result.trade_plans] == ["600089", "601138"]
    assert result.trade_plans[0].cost_signal_weight == Decimal("0.95")
    assert result.trade_plans[0].priority_score > result.trade_plans[1].priority_score
    assert "AI Chain" in result.trade_plans[0].chain_explanation
    assert "成本链权重" in result.trade_plans[0].rationale


def test_sentiment_snapshot_returns_trading_permission_contract() -> None:
    client = _client()

    response = client.get("/low-absorb/sentiment/snapshot")

    assert response.status_code == 200
    body = response.json()
    assert body["tradingPermission"]["status"] in {"允许", "观察", "拦截"}
    assert {gauge["id"] for gauge in body["gauges"]} == {"global", "a_share"}
    assert {panel["id"] for panel in body["instrumentPanels"]} == {
        "market_turnover",
        "limit_break",
        "advance_decline",
        "ai_capital_temperature",
        "global_risk_appetite",
        "sentiment_conclusion",
    }
    assert len(body["socialEvents"]) > 0
    assert len(body["newsEvents"]) > 0
