from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from src.low_absorb.config import LowAbsorbConfig
from src.low_absorb.data_provider import (
    ChainBranchStrength,
    DailyBar,
    FixtureMarketDataProvider,
    IntradayBar,
    MarketBreadth,
)
from src.low_absorb.scanner import LowAbsorbScanner


TRADE_DATE = date(2026, 6, 12)
SCAN_AT = datetime(2026, 6, 12, 14, 45)


def _config() -> LowAbsorbConfig:
    return LowAbsorbConfig(
        min_market_turnover_cny=Decimal("800000000000"),
        max_limit_break_rate=Decimal("0.50"),
        ma20_deviation_min=Decimal("-0.05"),
        ma20_deviation_max=Decimal("0.01"),
        max_volume_ratio_5d=Decimal("0.85"),
        min_lower_shadow_atr=Decimal("1.0"),
        max_data_staleness_seconds=60,
        max_single_position_weight=Decimal("0.12"),
        max_single_trade_risk_pct=Decimal("0.0035"),
    )


def _daily_bars(symbol: str = "601138", *, industry: str = "AI 服务器") -> list[DailyBar]:
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
                industry=industry,
                stock_name="工业富联",
                captured_at=SCAN_AT,
            )
        )
    bars.append(
        DailyBar(
            symbol=symbol,
            trade_date=TRADE_DATE,
            open=Decimal("19.10"),
            high=Decimal("19.05"),
            low=Decimal("18.00"),
            close=Decimal("19.20"),
            volume=Decimal("700000"),
            atr=Decimal("1.00"),
            industry=industry,
            stock_name="工业富联",
            captured_at=SCAN_AT,
        )
    )
    return bars


def _provider(
    *,
    symbols: list[str] | None = None,
    breadth: MarketBreadth | None = None,
    daily_bars: dict[str, list[DailyBar]] | None = None,
    branches: list[ChainBranchStrength] | None = None,
) -> FixtureMarketDataProvider:
    return FixtureMarketDataProvider(
        symbols=symbols or ["601138"],
        market_breadth=breadth
        or MarketBreadth(
            trade_date=TRADE_DATE,
            captured_at=SCAN_AT,
            total_market_turnover_cny=Decimal("900000000000"),
            limit_break_rate=Decimal("0.20"),
        ),
        daily_bars=daily_bars or {"601138": _daily_bars()},
        intraday_bars={
            "601138": [
                IntradayBar(
                    symbol="601138",
                    trade_date=TRADE_DATE,
                    at=datetime(2026, 6, 12, 14, 45),
                    open=Decimal("18.70"),
                    high=Decimal("18.96"),
                    low=Decimal("18.62"),
                    close=Decimal("18.88"),
                    volume=Decimal("120000"),
                )
            ]
        },
        chain_strength=branches
        or [
            ChainBranchStrength(
                branch_name="AI 服务器",
                rank=1,
                total_branches=3,
                slope=Decimal("0.08"),
                relative_strength=Decimal("1.20"),
            ),
            ChainBranchStrength(
                branch_name="光模块",
                rank=2,
                total_branches=3,
                slope=Decimal("0.03"),
                relative_strength=Decimal("1.05"),
            ),
            ChainBranchStrength(
                branch_name="AI 应用",
                rank=3,
                total_branches=3,
                slope=Decimal("-0.01"),
                relative_strength=Decimal("0.94"),
            ),
        ],
    )


def _scan(provider: FixtureMarketDataProvider, symbols: list[str] | None = None):
    scanner = LowAbsorbScanner(provider, _config())
    return scanner.scan_tail_session(TRADE_DATE, at=SCAN_AT, symbols=symbols)


def test_macro_fuse_when_limit_break_rate_is_52_percent() -> None:
    plans = _scan(
        _provider(
            breadth=MarketBreadth(
                trade_date=TRADE_DATE,
                captured_at=SCAN_AT,
                total_market_turnover_cny=Decimal("900000000000"),
                limit_break_rate=Decimal("0.52"),
            )
        )
    )

    assert plans == []


def test_stale_data_fails_closed() -> None:
    plans = _scan(
        _provider(
            breadth=MarketBreadth(
                trade_date=TRADE_DATE,
                captured_at=SCAN_AT - timedelta(seconds=61),
                total_market_turnover_cny=Decimal("900000000000"),
                limit_break_rate=Decimal("0.20"),
            )
        )
    )

    assert plans == []


def test_old_daily_bar_trade_date_fails_closed() -> None:
    bars: list[DailyBar] = []
    start_date = date(2026, 5, 18)
    for idx in range(19):
        trade_day = start_date + timedelta(days=idx)
        bars.append(
            DailyBar(
                symbol="601138",
                trade_date=trade_day,
                open=Decimal("20.00"),
                high=Decimal("20.30"),
                low=Decimal("19.80"),
                close=Decimal("20.00"),
                volume=Decimal("1000000"),
                atr=Decimal("1.00"),
                industry="AI 服务器",
                stock_name="工业富联",
                captured_at=datetime.combine(trade_day, datetime.min.time()),
            )
        )
    latest_old = date(2026, 6, 10)
    bars.append(
        DailyBar(
            symbol="601138",
            trade_date=latest_old,
            open=Decimal("19.10"),
            high=Decimal("19.05"),
            low=Decimal("18.00"),
            close=Decimal("19.20"),
            volume=Decimal("700000"),
            atr=Decimal("1.00"),
            industry="AI 服务器",
            stock_name="工业富联",
            captured_at=datetime.combine(latest_old, time(14, 45)),
        )
    )
    plans = _scan(_provider(daily_bars={"601138": bars}))
    assert plans == []


def test_non_mainboard_symbol_is_rejected() -> None:
    plans = _scan(
        _provider(symbols=["300001"], daily_bars={"300001": _daily_bars("300001")}),
        symbols=["300001"],
    )

    assert plans == []


def test_weak_ai_branch_is_rejected_when_rank_last_and_slope_negative() -> None:
    plans = _scan(
        _provider(
            branches=[
                ChainBranchStrength(
                    branch_name="AI 服务器",
                    rank=3,
                    total_branches=3,
                    slope=Decimal("-0.04"),
                    relative_strength=Decimal("0.88"),
                )
            ]
        )
    )

    assert plans == []


def test_ma20_deviation_rejection() -> None:
    bars = _daily_bars()
    bars[-1] = bars[-1].model_copy(update={"close": Decimal("21.00")})

    assert _scan(_provider(daily_bars={"601138": bars})) == []


def test_volume_ratio_rejection() -> None:
    bars = _daily_bars()
    bars[-1] = bars[-1].model_copy(update={"volume": Decimal("1200000")})

    assert _scan(_provider(daily_bars={"601138": bars})) == []


def test_lower_shadow_atr_rejection() -> None:
    bars = _daily_bars()
    bars[-1] = bars[-1].model_copy(update={"low": Decimal("18.55")})

    assert _scan(_provider(daily_bars={"601138": bars})) == []


def test_qualified_signal_creates_manual_trade_plan() -> None:
    plans = _scan(_provider())

    assert len(plans) == 1
    plan = plans[0]
    assert plan.stock_code == "601138"
    assert plan.stock_name == "工业富联"
    assert plan.entry_low == Decimal("18.62")
    assert plan.entry_high == Decimal("19.20")
    assert plan.stop_loss == Decimal("18.00")
    assert plan.planned_position_pct == Decimal("0.12")
    assert plan.initial_risk_cny == Decimal("120.00")
    assert plan.open_stop_risk_cny == Decimal("120.00")
    assert plan.r_multiple == Decimal("0.00")
    assert "MA20 偏离" in plan.rationale
    assert "人工低吸区间 18.62-19.20" in plan.manual_order_text
    assert "PENDING" not in plan.manual_order_text
