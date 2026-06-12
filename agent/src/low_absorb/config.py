"""Configuration schema for the AI Low Absorb manual workspace."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LowAbsorbConfig(BaseModel):
    """Runtime knobs for scans, manual plans, and risk supervision."""

    model_config = ConfigDict(extra="forbid")

    scan_time: time = time(14, 45)
    anti_noise_start: time = time(9, 30)
    anti_noise_end: time = time(10, 0)
    stop_supervision_time: time = time(10, 0)
    min_market_turnover_cny: Decimal = Field(default=Decimal("800000000000"), gt=0)
    max_limit_break_rate: Decimal = Field(default=Decimal("0.50"), ge=0, le=1)
    ma20_deviation_min: Decimal = Field(default=Decimal("-0.05"))
    ma20_deviation_max: Decimal = Field(default=Decimal("0.01"))
    max_volume_ratio_5d: Decimal = Field(default=Decimal("0.85"), gt=0)
    min_lower_shadow_atr: Decimal = Field(default=Decimal("1.0"), ge=0)
    morning_crash_pct: Decimal = Field(default=Decimal("-0.04"))
    alpha_relax_threshold: Decimal = Field(default=Decimal("0.01"), ge=0)
    max_relaxed_stop_tolerance: Decimal = Field(default=Decimal("0.015"), ge=0)
    notify_hold_warning: bool = True
    max_data_staleness_seconds: int = Field(default=60, gt=0)
    max_single_position_weight: Decimal = Field(default=Decimal("0.12"), gt=0, le=1)
    max_single_position_pct: Decimal = Field(default=Decimal("0.12"), gt=0, le=1)
    max_single_trade_risk_pct: Decimal = Field(default=Decimal("0.005"), gt=0, le=1)
    feishu_idempotency_ttl_seconds: int = Field(default=86_400, gt=0)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "LowAbsorbConfig":
        if self.ma20_deviation_min > self.ma20_deviation_max:
            raise ValueError("ma20_deviation_min must be <= ma20_deviation_max")
        return self
