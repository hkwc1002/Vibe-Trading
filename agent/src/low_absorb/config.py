"""Configuration schema for the AI Low Absorb manual workspace."""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _default_chain_cost_signal_weights() -> dict[str, Decimal]:
    return {
        "GPU/加速卡": Decimal("0.90"),
        "HBM/存储": Decimal("0.86"),
        "CPO/光模块": Decimal("0.82"),
        "PCB/高速板": Decimal("0.74"),
        "服务器ODM": Decimal("0.70"),
        "液冷散热": Decimal("0.66"),
        "电源连接器": Decimal("0.62"),
    }


class LowAbsorbConfig(BaseModel):
    """Runtime knobs for scans, manual plans, and risk supervision."""

    model_config = ConfigDict(extra="forbid")

    scan_time: time = time(14, 45)
    anti_noise_start: time = time(9, 30)
    anti_noise_end: time = time(10, 0)
    stop_supervision_time: time = time(10, 0)
    min_market_turnover_cny: Decimal = Field(default=Decimal("500000000000"), gt=0)
    max_limit_break_rate: Decimal = Field(default=Decimal("0.45"), ge=0, le=1)
    ma20_deviation_min: Decimal = Field(default=Decimal("0"))
    ma20_deviation_max: Decimal = Field(default=Decimal("0.012"))
    max_volume_ratio_5d: Decimal = Field(default=Decimal("0.65"), gt=0)
    min_lower_shadow_atr: Decimal = Field(default=Decimal("0.5"), ge=0)
    morning_crash_pct: Decimal = Field(default=Decimal("-0.04"))
    alpha_relax_threshold: Decimal = Field(default=Decimal("0.01"), ge=0)
    max_relaxed_stop_tolerance: Decimal = Field(default=Decimal("0.015"), ge=0)
    notify_hold_warning: bool = True
    max_data_staleness_seconds: int = Field(default=60, gt=0)
    max_single_position_weight: Decimal = Field(default=Decimal("0.12"), gt=0, le=1)
    max_single_position_pct: Decimal = Field(default=Decimal("0.12"), gt=0, le=1)
    max_single_trade_risk_pct: Decimal = Field(default=Decimal("0.005"), gt=0, le=1)
    feishu_idempotency_ttl_seconds: int = Field(default=86_400, gt=0)
    active_cost_chain_version: str = "GB300 NVL72"
    chain_cost_signal_weights: dict[str, Decimal] = Field(default_factory=_default_chain_cost_signal_weights)
    data_provider_mode: Literal["auto", "real", "fixture"] = "auto"
    enable_fixture_fallback: bool = True
    global_market_provider: Literal["auto", "yfinance", "stooq"] = "auto"
    eastmoney_min_interval_seconds: Decimal = Field(default=Decimal("1.0"), gt=0)

    # ── Data source quality settings ───────────────────────────────────────
    data_source_failure_threshold: int = Field(default=3, ge=1, description="Consecutive failures before circuit opens")
    data_source_cooldown_seconds: int = Field(default=60, ge=0, description="Circuit breaker cooldown in seconds")
    data_conflict_tolerance_pct: Decimal = Field(default=Decimal("0.02"), ge=0, description="Max acceptable difference % between sources")
    data_production_mode: bool = Field(default=False, description="When True, fixture fallback is forbidden; all failing must fail-closed")

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "LowAbsorbConfig":
        if self.ma20_deviation_min > self.ma20_deviation_max:
            raise ValueError("ma20_deviation_min must be <= ma20_deviation_max")
        return self
