"""Storage boundary for Low Absorb workspace state."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Protocol

from .config import LowAbsorbConfig
from .chain_matrix import default_cost_chain_models
from .models import (
    CloseReport,
    CostChainModel,
    FeishuNotificationResult,
    LowAbsorbSignal,
    ManualFill,
    ManualPosition,
    ManualTradePlan,
)


class LowAbsorbRepository(Protocol):
    """Repository contract for the manual-execution Low Absorb workspace."""

    signals: MutableMapping[str, LowAbsorbSignal]
    trade_plans: MutableMapping[str, ManualTradePlan]
    fills: MutableMapping[str, ManualFill]
    positions: MutableMapping[str, ManualPosition]
    notifications: MutableMapping[str, FeishuNotificationResult]
    reports: MutableMapping[str, CloseReport]

    def clear(self) -> None:
        """Remove all persisted workspace state."""

    def seed(
        self,
        *,
        signals: list[LowAbsorbSignal] | None = None,
        trade_plans: list[ManualTradePlan] | None = None,
        fills: list[ManualFill] | None = None,
        positions: list[ManualPosition] | None = None,
    ) -> None:
        """Seed state for tests or local fixtures."""

    def save(self) -> None:
        """Persist current state if the repository is durable."""

    def get_config(self) -> LowAbsorbConfig:
        """Return strategy/runtime settings."""

    def update_config(self, updates: dict[str, Any]) -> LowAbsorbConfig:
        """Patch strategy/runtime settings."""

    def get_webhook(self) -> str | None:
        """Return the private Feishu webhook."""

    def update_webhook(self, webhook: str | None) -> None:
        """Persist the private Feishu webhook."""

    def get_cost_chain_models(self) -> dict[str, CostChainModel]:
        """Return versioned NVIDIA AI server cost-chain models."""

    def update_cost_chain_model(self, version: str, components: list[Any]) -> CostChainModel:
        """Persist an editable cost-chain model version."""


class InMemoryLowAbsorbStorage:
    """Minimal in-memory storage useful for tests and API skeletons."""

    def __init__(self) -> None:
        self.signals: dict[str, LowAbsorbSignal] = {}
        self.trade_plans: dict[str, ManualTradePlan] = {}
        self.fills: dict[str, ManualFill] = {}
        self.positions: dict[str, ManualPosition] = {}
        self.notifications: dict[str, FeishuNotificationResult] = {}
        self.reports: dict[str, CloseReport] = {}
        self._config = LowAbsorbConfig()
        self._feishu_webhook: str | None = None
        self._cost_chain_models: dict[str, CostChainModel] = default_cost_chain_models()

    def clear(self) -> None:
        self.signals.clear()
        self.trade_plans.clear()
        self.fills.clear()
        self.positions.clear()
        self.notifications.clear()
        self.reports.clear()
        self.save()

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
        self.save()

    def save(self) -> None:
        """No-op persistence hook for tests."""

    def get_config(self) -> LowAbsorbConfig:
        return self._config

    def update_config(self, updates: dict[str, Any]) -> LowAbsorbConfig:
        self._config = LowAbsorbConfig.model_validate({**self._config.model_dump(), **updates})
        self.save()
        return self._config

    def get_webhook(self) -> str | None:
        return self._feishu_webhook

    def update_webhook(self, webhook: str | None) -> None:
        self._feishu_webhook = webhook
        self.save()

    def get_cost_chain_models(self) -> dict[str, CostChainModel]:
        return self._cost_chain_models

    def update_cost_chain_model(self, version: str, components: list[Any]) -> CostChainModel:
        if version != "custom/manual":
            raise ValueError("only custom/manual cost-chain model can be updated")
        current = self._cost_chain_models.get(version)
        if current is None:
            current = CostChainModel(version="custom/manual", is_editable=True)
        if not current.is_editable:
            raise ValueError("only editable cost-chain models can be updated")
        parsed = [
            item if hasattr(item, "model_dump") else item
            for item in components
        ]
        updated = CostChainModel.model_validate(
            {
                "version": version,
                "is_editable": True,
                "components": [
                    item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                    for item in parsed
                ],
            }
        )
        self._cost_chain_models[version] = updated
        weights = {
            component.related_sector: component.signal_weight
            for component in updated.components
        }
        self._config = self._config.model_copy(update={"chain_cost_signal_weights": weights})
        self.save()
        return updated


class JsonLowAbsorbStorage(InMemoryLowAbsorbStorage):
    """JSON-backed repository for local/dev Low Absorb state."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else self.default_path()
        super().__init__()
        self._load()

    @staticmethod
    def default_path() -> Path:
        return Path(__file__).resolve().parents[2] / ".ui_runtime" / "low_absorb" / "state.json"

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "signals": [item.model_dump(mode="json") for item in self.signals.values()],
            "trade_plans": [item.model_dump(mode="json") for item in self.trade_plans.values()],
            "fills": [item.model_dump(mode="json") for item in self.fills.values()],
            "positions": [item.model_dump(mode="json") for item in self.positions.values()],
            "notifications": [item.model_dump(mode="json") for item in self.notifications.values()],
            "reports": [item.model_dump(mode="json") for item in self.reports.values()],
            "settings": {
                "config": self._config.model_dump(mode="json"),
                "feishu_webhook": self._feishu_webhook,
                "cost_chain_models": [
                    item.model_dump(mode="json") for item in self._cost_chain_models.values()
                ],
            },
        }
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.path)

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        self.signals = {
            item.signal_id: item
            for item in (LowAbsorbSignal.model_validate(row) for row in payload.get("signals", []))
        }
        self.trade_plans = {
            item.plan_id: item
            for item in (ManualTradePlan.model_validate(row) for row in payload.get("trade_plans", []))
        }
        self.fills = {
            item.fill_id: item
            for item in (ManualFill.model_validate(row) for row in payload.get("fills", []))
        }
        self.positions = {
            item.position_id: item
            for item in (ManualPosition.model_validate(row) for row in payload.get("positions", []))
        }
        self.notifications = {
            item.idempotency_key: item
            for item in (FeishuNotificationResult.model_validate(row) for row in payload.get("notifications", []))
        }
        self.reports = {
            item.report_id: item
            for item in (CloseReport.model_validate(row) for row in payload.get("reports", []))
        }
        settings = payload.get("settings", {})
        config_payload = settings.get("config")
        if isinstance(config_payload, dict):
            self._config = LowAbsorbConfig.model_validate(config_payload)
        webhook = settings.get("feishu_webhook")
        self._feishu_webhook = webhook if isinstance(webhook, str) and webhook else None
        cost_models = settings.get("cost_chain_models")
        if isinstance(cost_models, list):
            parsed = [CostChainModel.model_validate(row) for row in cost_models]
            self._cost_chain_models = {item.version: item for item in parsed}
