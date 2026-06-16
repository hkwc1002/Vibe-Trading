"""Pydantic models for the AI Low Absorb manual-execution flow."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class NotificationType(str, Enum):
    BUY_RECOMMENDATION = "BUY_RECOMMENDATION"
    CLOSE_REPORT = "CLOSE_REPORT"
    MORNING_RISK_ALERT = "MORNING_RISK_ALERT"
    FILL_REMINDER = "FILL_REMINDER"
    NOTIFIER_TEST = "NOTIFIER_TEST"


FeishuNotificationType = Literal[
    "buy_recommendation",
    "close_report",
    "risk_alert_10_00",
    "fill_reminder",
    "notifier_test",
]


class SignalStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    RECOMMENDED = "RECOMMENDED"
    SENT_TO_FEISHU = "SENT_TO_FEISHU"
    INVALIDATED = "INVALIDATED"


class TradePlanStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    SENT_TO_FEISHU = "SENT_TO_FEISHU"
    MANUAL_FILLED = "MANUAL_FILLED"
    INVALIDATED = "INVALIDATED"


class PositionStatus(str, Enum):
    ACTIVE_POSITION = "ACTIVE_POSITION"
    HOLDING_REVIEW = "HOLDING_REVIEW"
    EXIT_SUGGESTED = "EXIT_SUGGESTED"
    MANUAL_EXITED = "MANUAL_EXITED"
    CLOSED = "CLOSED"
    INVALIDATED = "INVALIDATED"


class RiskSupervisionStatus(str, Enum):
    HOLD_NOISE = "HOLD_NOISE"
    HOLD_WITH_WARNING = "HOLD_WITH_WARNING"
    EXIT_SUGGESTED = "EXIT_SUGGESTED"
    CRASH_WARNING = "CRASH_WARNING"


TRADE_FLOW_STATES: tuple[str, ...] = (
    "CANDIDATE",
    "RECOMMENDED",
    "SENT_TO_FEISHU",
    "MANUAL_FILLED",
    "ACTIVE_POSITION",
    "HOLDING_REVIEW",
    "EXIT_SUGGESTED",
    "MANUAL_EXITED",
    "CLOSED",
    "INVALIDATED",
)

MAINBOARD_PREFIXES: tuple[str, ...] = ("000", "001", "002", "003", "600", "601", "603", "605")


def _normalize_stock_code(stock_code: str) -> str:
    code = stock_code.strip().upper()
    if code.startswith(("SH", "SZ")):
        code = code[2:]
    if len(code) != 6 or not code.isdigit() or not code.startswith(MAINBOARD_PREFIXES):
        raise ValueError("stock_code must be a domestic mainboard 6-digit code")
    return code


class LowAbsorbBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class StockIdentityModel(LowAbsorbBaseModel):
    stock_code: str = Field(..., min_length=6, max_length=8)
    stock_name: str = Field(..., min_length=1)

    @field_validator("stock_code")
    @classmethod
    def validate_stock_code(cls, stock_code: str) -> str:
        return _normalize_stock_code(stock_code)


class LowAbsorbSignal(StockIdentityModel):
    signal_id: str = Field(..., min_length=1)
    trade_date: date
    branch_name: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1)
    ma20_deviation_pct: Decimal
    volume_ratio: Decimal = Field(..., ge=0)
    lower_shadow_atr: Decimal = Field(..., ge=0)
    reason: str = Field(..., min_length=1)
    intercept_reasons: list[str] = Field(default_factory=list)
    status: SignalStatus = SignalStatus.CANDIDATE
    chain_explanation: str = ""
    branch_strength: Decimal = Decimal("0")
    cost_signal_weight: Decimal = Decimal("0")
    priority_score: Decimal = Decimal("0")
    downgrade_reason: str = ""
    block_reason: str = ""
    sector_role: str = ""


class ManualTradePlan(StockIdentityModel):
    plan_id: str = Field(..., min_length=1)
    signal_id: str = Field(..., min_length=1)
    trade_date: date
    entry_low: Decimal = Field(..., gt=0)
    entry_high: Decimal = Field(..., gt=0)
    stop_loss: Decimal = Field(..., ge=0)
    planned_position_pct: Decimal = Field(..., gt=0, le=1)
    max_risk_pct: Decimal = Field(..., gt=0, le=1)
    initial_risk_r: Decimal = Field(..., gt=0)
    initial_risk_cny: Decimal = Field(default=Decimal("0"), ge=0)
    open_stop_risk_cny: Decimal = Field(default=Decimal("0"), ge=0)
    r_multiple: Decimal = Decimal("0")
    rationale: str = ""
    manual_order_text: str = Field(..., min_length=1)
    feishu_idempotency_key: str | None = None
    status: TradePlanStatus = TradePlanStatus.RECOMMENDED
    chain_explanation: str = ""
    branch_strength: Decimal = Decimal("0")
    cost_signal_weight: Decimal = Decimal("0")
    priority_score: Decimal = Decimal("0")
    downgrade_reason: str = ""
    block_reason: str = ""
    sector_role: str = ""

    @model_validator(mode="after")
    def validate_price_ladder(self) -> "ManualTradePlan":
        if self.entry_high < self.entry_low:
            raise ValueError("entry_high must be greater than or equal to entry_low")
        if self.stop_loss >= self.entry_low:
            raise ValueError("stop_loss must be lower than entry_low")
        return self


class ManualFill(StockIdentityModel):
    fill_id: str = Field(..., min_length=1)
    plan_id: str | None = None
    signal_id: str | None = None
    side: Literal["BUY", "SELL"] = "BUY"
    planned_price: Decimal | None = Field(default=None, gt=0)
    actual_price: Decimal | None = Field(default=None, gt=0)
    fill_price: Decimal | None = Field(default=None, gt=0)
    quantity: int = Field(..., gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    fees: Decimal = Field(default=Decimal("0"), ge=0)
    executed_at: datetime | None = None
    filled_at: datetime | None = None
    slippage: Decimal | None = None
    execution_note: str | None = None
    subjective_reason: str | None = None
    note: str = ""

    @model_validator(mode="after")
    def normalize_fill_prices_and_time(self) -> "ManualFill":
        actual_price = self.actual_price or self.fill_price
        if actual_price is None:
            raise ValueError("actual_price is required")
        executed_at = self.executed_at or self.filled_at
        if executed_at is None:
            raise ValueError("executed_at is required")

        object.__setattr__(self, "actual_price", actual_price)
        object.__setattr__(self, "fill_price", actual_price)
        object.__setattr__(self, "executed_at", executed_at)
        object.__setattr__(self, "filled_at", executed_at)
        if self.fee == 0 and self.fees != 0:
            object.__setattr__(self, "fee", self.fees)
        if self.fees == 0 and self.fee != 0:
            object.__setattr__(self, "fees", self.fee)
        object.__setattr__(
            self,
            "slippage",
            actual_price - self.planned_price if self.planned_price is not None else None,
        )
        return self


class ManualPosition(StockIdentityModel):
    position_id: str = Field(..., min_length=1)
    plan_id: str | None = None
    branch: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    cost_price: Decimal | None = Field(default=None, gt=0)
    avg_cost: Decimal | None = Field(default=None, gt=0)
    current_price: Decimal | None = Field(default=None, gt=0)
    stop_loss: Decimal | None = Field(default=None, ge=0)
    initial_stop_price: Decimal | None = Field(default=None, ge=0)
    current_stop_price: Decimal | None = Field(default=None, ge=0)
    quantity: int = Field(..., ge=0)
    position_pct: Decimal | None = Field(default=None, gt=0, le=1)
    position_weight: Decimal | None = Field(default=None, gt=0, le=1)
    status: PositionStatus = PositionStatus.ACTIVE_POSITION
    notes: list[str] = Field(default_factory=list)
    note: str = ""

    @model_validator(mode="after")
    def normalize_position_fields(self) -> "ManualPosition":
        avg_cost = self.avg_cost or self.cost_price
        if avg_cost is None:
            raise ValueError("avg_cost is required")
        initial_stop = self.initial_stop_price or self.stop_loss
        if initial_stop is None:
            raise ValueError("initial_stop_price is required")
        current_stop = self.current_stop_price or self.stop_loss or initial_stop
        object.__setattr__(self, "avg_cost", avg_cost)
        object.__setattr__(self, "cost_price", avg_cost)
        object.__setattr__(self, "initial_stop_price", initial_stop)
        object.__setattr__(self, "current_stop_price", current_stop)
        object.__setattr__(self, "stop_loss", current_stop)
        if self.position_weight is None and self.position_pct is not None:
            object.__setattr__(self, "position_weight", self.position_pct)
        if self.position_pct is None and self.position_weight is not None:
            object.__setattr__(self, "position_pct", self.position_weight)
        return self


class PositionRisk(StockIdentityModel):
    position_id: str = ""
    initial_risk_amount: Decimal = Field(..., ge=0)
    current_risk_amount: Decimal = Field(..., ge=0)
    initial_risk_cny: Decimal = Field(default=Decimal("0"), ge=0)
    current_stop_risk_cny: Decimal = Field(default=Decimal("0"), ge=0)
    r_multiple: Decimal
    max_loss_pct_of_equity: Decimal | None = None
    supervision_status: str = ""
    risk_level: Literal["normal", "watch", "warning", "danger"]
    needs_supervision: bool


class CostChainComponent(LowAbsorbBaseModel):
    component: str = Field(..., min_length=1)
    cost_weight: Decimal = Field(..., ge=0, le=1)
    cost_weight_range: list[Decimal] = Field(default_factory=list, max_length=2)
    cost_increase_vs_previous_generation: Decimal
    related_sector: str = Field(..., min_length=1)
    a_share_leaders: list[str] = Field(default_factory=list)
    tradable_mainboard_mapping: list[str] = Field(default_factory=list)
    signal_weight: Decimal = Field(..., ge=0, le=1)
    data_source: str = Field(..., min_length=1)
    source_type: str = "manual"
    source_url: str = ""
    source_title: str = ""
    confidence: Literal["high", "medium", "low"] = "low"
    is_estimated: bool = True
    methodology_note: str = ""
    as_of: date


class CostChainModel(LowAbsorbBaseModel):
    version: str = Field(..., min_length=1)
    is_editable: bool = False
    components: list[CostChainComponent] = Field(default_factory=list)
    status: str | None = None  # None = ACTIVE (backward compat)


class ChainSectorStock(LowAbsorbBaseModel):
    role: Literal["leader", "core_middle_cap", "sentiment_stock", "mainboard_mapping", "watch_only"]
    stock_code: str = Field(..., min_length=1)
    stock_name: str = Field(..., min_length=1)
    strength_score: Decimal = Field(..., ge=0, le=100)
    volume_condition: str = Field(..., min_length=1)
    low_absorb_suitability: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    current_recommendation: str = Field(..., min_length=1)


class ChainSectorWorkspace(LowAbsorbBaseModel):
    sector_id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    sector_index: str = Field(..., min_length=1)
    price_change_pct: Decimal
    turnover_cny: Decimal = Field(..., ge=0)
    volume_ratio: Decimal = Field(..., ge=0)
    rs_strength: Decimal
    fund_flow_cny: Decimal
    trend_slope: Decimal
    limit_up_count: int = Field(..., ge=0)
    limit_break_count: int = Field(..., ge=0)
    stocks: list[ChainSectorStock] = Field(default_factory=list, max_length=5)


class MorningSupervisionResult(StockIdentityModel):
    position_id: str = Field(..., min_length=1)
    observed_at: datetime
    status: RiskSupervisionStatus
    should_notify_feishu: bool
    open_price: Decimal = Field(..., gt=0)
    current_price: Decimal = Field(..., gt=0)
    first_30m_close: Decimal | None = Field(default=None, gt=0)
    stock_return_30m: Decimal | None = None
    industry_return_30m: Decimal | None = None
    industry_alpha: Decimal | None = None
    stop_break_pct: Decimal | None = None
    reason: str = Field(..., min_length=1)
    recommendation: str = Field(..., min_length=1)


class SentimentSnapshot(LowAbsorbBaseModel):
    trade_date: date
    snapshot_at: datetime
    macro_score: Decimal = Field(..., ge=-1, le=1)
    gate_passed: bool
    summary: str = Field(..., min_length=1)


class ChainBranchSnapshot(LowAbsorbBaseModel):
    trade_date: date
    branch_name: str = Field(..., min_length=1)
    relative_strength: Decimal
    gate_passed: bool
    leaders: list[str] = Field(default_factory=list)

    @field_validator("leaders")
    @classmethod
    def validate_leaders(cls, leaders: list[str]) -> list[str]:
        return [_normalize_stock_code(code) for code in leaders]


class CloseReport(LowAbsorbBaseModel):
    report_id: str = Field(..., min_length=1)
    trade_date: date
    summary: str = Field(..., min_length=1)
    signals: list[LowAbsorbSignal] = Field(default_factory=list)
    trade_plans: list[ManualTradePlan] = Field(default_factory=list)
    positions: list[ManualPosition] = Field(default_factory=list)
    review_items: list[str] = Field(default_factory=list)


class FeishuNotificationResult(LowAbsorbBaseModel):
    notification_id: str = Field(default="", min_length=0)
    ok: bool = False
    notification_type: NotificationType | FeishuNotificationType
    idempotency_key: str = Field(..., min_length=1)
    sent_at: datetime | None = None
    skipped: bool = False
    error: str | None = None
    sent: bool = False
    message: str = Field(default="", min_length=0)


class FeishuSendPolicy(LowAbsorbBaseModel):
    """Current Feishu notification send policy derived from env and config."""

    real_send_enabled: bool
    webhook_configured: bool
    masked_webhook: str | None = None


class FeishuNotificationAudit(LowAbsorbBaseModel):
    """Audit record for a single Feishu notification attempt."""

    notification_id: str = Field(..., min_length=1)
    notification_type: str
    target_id: str | None = None
    idempotency_key: str = Field(..., min_length=1)
    real_send: bool = False
    ok: bool = False
    error: str | None = None
    sent_at: datetime | None = None


# ── Backtest models ───────────────────────────────────────────────────────

BACKTEST_RUN_STATUSES = ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED")
"""Allowed BacktestRun statuses."""


class BacktestRunRequest(LowAbsorbBaseModel):
    """Request to run a daily-level backtest."""

    start_date: date
    end_date: date
    symbols: list[str] | None = None
    cost_chain_version: str = Field(default="GB200 NVL72", min_length=1)
    config_snapshot_id: str | None = None
    include_manual_fill_assumption: bool = False


class BacktestRun(LowAbsorbBaseModel):
    """A single backtest run with lifecycle status."""

    run_id: str = Field(..., min_length=1)
    request: BacktestRunRequest
    status: str = Field(default="QUEUED", pattern="^(QUEUED|RUNNING|SUCCEEDED|FAILED)$")
    created_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    error: str | None = None


class BacktestBranchAttribution(LowAbsorbBaseModel):
    """Per-branch contribution to overall backtest performance."""

    branch: str
    sample_count: int = Field(..., ge=0)
    average_r: Decimal
    contribution_pct: Decimal = Field(..., ge=0, le=1)


class BacktestSensitivityRow(LowAbsorbBaseModel):
    """Sensitivity analysis for a single parameter variant."""

    parameter: str
    base: Decimal
    variant: Decimal
    description: str = ""


class BacktestResult(LowAbsorbBaseModel):
    """Complete backtest result with metrics and attribution."""

    run_id: str = Field(..., min_length=1)
    status: str = "SUCCEEDED"
    error: str | None = None
    data_sources: list[str] = Field(default_factory=lambda: ["fixture"])
    sample_count: int = Field(default=0, ge=0)
    signal_count: int = Field(default=0, ge=0)
    plan_count: int = Field(default=0, ge=0)
    win_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    average_r: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    branch_attribution: list[BacktestBranchAttribution] = Field(default_factory=list)
    sensitivity: list[BacktestSensitivityRow] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
