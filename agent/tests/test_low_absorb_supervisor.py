from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from src.low_absorb.config import LowAbsorbConfig
from src.low_absorb.data_provider import FixtureMarketDataProvider, IntradayBar
from src.low_absorb.models import ManualPosition, RiskSupervisionStatus
from src.low_absorb.notifier import FeishuNotifier
from src.low_absorb.risk import calculate_position_risk
from src.low_absorb.storage import InMemoryLowAbsorbStorage
from src.low_absorb.supervisor import supervise_position_morning


TRADE_DATE = date(2026, 6, 15)


def _config() -> LowAbsorbConfig:
    return LowAbsorbConfig(
        morning_crash_pct=Decimal("-0.04"),
        alpha_relax_threshold=Decimal("0.01"),
        max_relaxed_stop_tolerance=Decimal("0.015"),
        notify_hold_warning=True,
    )


def _position() -> ManualPosition:
    return ManualPosition(
        position_id="pos-601138-20260612",
        plan_id="plan-601138-20260612",
        stock_code="601138",
        stock_name="Foxconn Industrial Internet",
        branch="AI Server",
        opened_at=datetime(2026, 6, 12, 14, 55),
        avg_cost=Decimal("18.78"),
        current_price=Decimal("18.20"),
        initial_stop_price=Decimal("17.88"),
        current_stop_price=Decimal("17.88"),
        quantity=1000,
        position_weight=Decimal("0.12"),
    )


def _provider(
    *,
    intraday_close: Decimal,
    intraday_open: Decimal = Decimal("18.80"),
    industry_return: Decimal = Decimal("0"),
    at: datetime = datetime(2026, 6, 15, 10, 0),
) -> FixtureMarketDataProvider:
    return FixtureMarketDataProvider(
        intraday_bars={
            "601138": [
                IntradayBar(
                    symbol="601138",
                    trade_date=TRADE_DATE,
                    at=at,
                    open=intraday_open,
                    high=max(intraday_open, intraday_close),
                    low=min(intraday_open, intraday_close),
                    close=intraday_close,
                    volume=Decimal("180000"),
                )
            ]
        },
        industry_returns={"AI Server": industry_return},
    )


def test_0942_minor_break_returns_hold_noise_without_feishu() -> None:
    result = supervise_position_morning(
        position=_position(),
        provider=_provider(intraday_close=Decimal("18.68"), at=datetime(2026, 6, 15, 9, 42)),
        trade_date=TRADE_DATE,
        observed_at=datetime(2026, 6, 15, 9, 42),
        config=_config(),
    )

    assert result.status is RiskSupervisionStatus.HOLD_NOISE
    assert result.should_notify_feishu is False


def test_0942_crash_returns_crash_warning_and_feishu_alert() -> None:
    result = supervise_position_morning(
        position=_position(),
        provider=_provider(intraday_close=Decimal("18.04"), at=datetime(2026, 6, 15, 9, 42)),
        trade_date=TRADE_DATE,
        observed_at=datetime(2026, 6, 15, 9, 42),
        config=_config(),
    )

    assert result.status is RiskSupervisionStatus.CRASH_WARNING
    assert result.should_notify_feishu is True


def test_1000_close_above_stop_returns_hold_noise() -> None:
    result = supervise_position_morning(
        position=_position(),
        provider=_provider(intraday_close=Decimal("18.00")),
        trade_date=TRADE_DATE,
        observed_at=datetime(2026, 6, 15, 10, 0),
        config=_config(),
    )

    assert result.status is RiskSupervisionStatus.HOLD_NOISE
    assert result.should_notify_feishu is False


def test_1000_below_stop_and_weak_vs_industry_returns_exit_suggested() -> None:
    result = supervise_position_morning(
        position=_position(),
        provider=_provider(intraday_close=Decimal("17.70"), industry_return=Decimal("-0.01")),
        trade_date=TRADE_DATE,
        observed_at=datetime(2026, 6, 15, 10, 0),
        config=_config(),
    )

    assert result.status is RiskSupervisionStatus.EXIT_SUGGESTED
    assert result.should_notify_feishu is True


def test_1000_below_stop_but_strong_alpha_returns_hold_with_warning() -> None:
    result = supervise_position_morning(
        position=_position(),
        provider=_provider(intraday_close=Decimal("17.80"), industry_return=Decimal("-0.07")),
        trade_date=TRADE_DATE,
        observed_at=datetime(2026, 6, 15, 10, 0),
        config=_config(),
    )

    assert result.status is RiskSupervisionStatus.HOLD_WITH_WARNING
    assert result.should_notify_feishu is True


def test_relaxed_stop_tolerance_prevents_unlimited_tolerance() -> None:
    result = supervise_position_morning(
        position=_position(),
        provider=_provider(intraday_close=Decimal("17.50"), industry_return=Decimal("-0.085")),
        trade_date=TRADE_DATE,
        observed_at=datetime(2026, 6, 15, 10, 0),
        config=_config(),
    )

    assert result.status is RiskSupervisionStatus.EXIT_SUGGESTED
    assert result.should_notify_feishu is True


def test_feishu_idempotency_on_risk_alerts() -> None:
    import os

    calls: list[dict[str, object]] = []

    def transport(url: str, payload: dict[str, object]) -> tuple[int, str]:
        calls.append(payload)
        return 200, "ok"

    storage = InMemoryLowAbsorbStorage()
    notifier = FeishuNotifier(
        webhook_url="https://open.feishu.cn/webhook/test",
        storage=storage,
        transport=transport,
    )
    position = _position()
    risk = calculate_position_risk(position)

    old = os.environ.get("LOW_ABSORB_FEISHU_REAL_SEND")
    os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = "true"
    try:
        first = notifier.send_risk_alert(
            position=position,
            risk=risk,
            first_30m_close=Decimal("17.70"),
            industry_alpha=Decimal("-0.04"),
            supervision_status=RiskSupervisionStatus.EXIT_SUGGESTED.value,
        )
        second = notifier.send_risk_alert(
            position=position,
            risk=risk,
            first_30m_close=Decimal("17.70"),
            industry_alpha=Decimal("-0.04"),
            supervision_status=RiskSupervisionStatus.EXIT_SUGGESTED.value,
        )
    finally:
        if old is not None:
            os.environ["LOW_ABSORB_FEISHU_REAL_SEND"] = old
        else:
            os.environ.pop("LOW_ABSORB_FEISHU_REAL_SEND", None)

    assert first.ok is True
    assert second.ok is True
    assert second.skipped is True
    assert len(calls) == 1
