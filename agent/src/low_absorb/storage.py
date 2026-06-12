"""Storage boundary for Low Absorb workspace state."""

from __future__ import annotations

from .models import (
    CloseReport,
    FeishuNotificationResult,
    LowAbsorbSignal,
    ManualFill,
    ManualPosition,
    ManualTradePlan,
)


class InMemoryLowAbsorbStorage:
    """Minimal in-memory storage useful for tests and API skeletons."""

    def __init__(self) -> None:
        self.signals: dict[str, LowAbsorbSignal] = {}
        self.trade_plans: dict[str, ManualTradePlan] = {}
        self.fills: dict[str, ManualFill] = {}
        self.positions: dict[str, ManualPosition] = {}
        self.notifications: dict[str, FeishuNotificationResult] = {}
        self.reports: dict[str, CloseReport] = {}

    def clear(self) -> None:
        self.signals.clear()
        self.trade_plans.clear()
        self.fills.clear()
        self.positions.clear()
        self.notifications.clear()
        self.reports.clear()

    def seed(
        self,
        *,
        signals: list[LowAbsorbSignal] | None = None,
        trade_plans: list[ManualTradePlan] | None = None,
        fills: list[ManualFill] | None = None,
        positions: list[ManualPosition] | None = None,
    ) -> None:
        for signal in signals or []:
            self.signals[signal.signal_id] = signal
        for plan in trade_plans or []:
            self.trade_plans[plan.plan_id] = plan
        for fill in fills or []:
            self.fills[fill.fill_id] = fill
        for position in positions or []:
            self.positions[position.position_id] = position
