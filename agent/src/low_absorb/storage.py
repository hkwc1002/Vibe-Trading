"""Storage boundary for Low Absorb workspace state."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from datetime import datetime as _dt
from pathlib import Path
from typing import Any, Protocol

from .config import LowAbsorbConfig
from .chain_matrix import default_cost_chain_models
from .cost_chain.models import CostChainAudit, CostChainCandidate, CostChainCandidateStatus
from .models import (
    BacktestResult,
    BacktestRun,
    CloseReport,
    CostChainModel,
    FeishuNotificationResult,
    LowAbsorbSignal,
    ManualFill,
    ManualPosition,
    ManualTradePlan,
)


MAX_BACKTEST_RUNS = 50


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
        self.candidates: dict[str, CostChainCandidate] = {}
        self.audit_log: list[CostChainAudit] = []
        self.backtest_runs: dict[str, BacktestRun] = {}
        self.backtest_results: dict[str, BacktestResult] = {}
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
        self.candidates.clear()
        self.audit_log.clear()
        self.backtest_runs.clear()
        self.backtest_results.clear()
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

    def create_candidate(self, candidate: CostChainCandidate) -> CostChainCandidate:
        """Store a new candidate version and record audit entry."""
        self.candidates[candidate.candidate_id] = candidate
        self.audit_log.append(CostChainAudit(
            audit_id=f"audit-{candidate.candidate_id}-created",
            candidate_id=candidate.candidate_id,
            action="created",
            after_version=candidate.version,
            actor=candidate.source_name,
            created_at=candidate.created_at,
        ))
        self.save()
        return candidate

    def list_candidates(self) -> list[CostChainCandidate]:
        """Return all candidates sorted by creation time descending."""
        return sorted(self.candidates.values(), key=lambda c: c.created_at, reverse=True)

    def get_candidate(self, candidate_id: str) -> CostChainCandidate | None:
        """Look up a candidate by ID."""
        return self.candidates.get(candidate_id)

    def update_candidate_status(
        self,
        candidate_id: str,
        new_status: CostChainCandidateStatus,
        review_note: str | None = None,
    ) -> CostChainCandidate:
        """Update candidate status (approve/reject). If ACTIVE, also promote its version."""
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")

        updated = candidate.model_copy(update={
            "status": new_status,
            "reviewed_at": _dt.now(),
            "review_note": review_note,
        })
        self.candidates[candidate_id] = updated

        action = new_status.value.lower()
        self.audit_log.append(CostChainAudit(
            audit_id=f"audit-{candidate_id}-{action}",
            candidate_id=candidate_id,
            action=action,
            before_version=None,
            after_version=updated.version,
            actor="user",
            created_at=_dt.now(),
            note=review_note,
        ))

        # If approved → set as ACTIVE and promote to cost_chain_models
        if new_status == CostChainCandidateStatus.APPROVED:
            promoting_version = updated.version

            # Deactivate other active versions (status=None or ACTIVE)
            for ver, model in list(self._cost_chain_models.items()):
                if (model.status is None or model.status == "ACTIVE") and ver != promoting_version:
                    self._cost_chain_models[ver] = model.model_copy(update={"status": "ROLLED_BACK"})

            # Mark candidate ACTIVE
            active = updated.model_copy(update={"status": CostChainCandidateStatus.ACTIVE})
            self.candidates[candidate_id] = active
            # Build a CostChainModel from the candidate's components
            new_model = CostChainModel(
                version=active.version,
                is_editable=False,
                components=active.components,
                status="ACTIVE",
            )
            self._cost_chain_models[active.version] = new_model
            self.audit_log.append(CostChainAudit(
                audit_id=f"audit-{candidate_id}-activated",
                candidate_id=candidate_id,
                action="activated",
                after_version=active.version,
                actor="system",
                created_at=_dt.now(),
                note="Candidate approved and activated",
            ))

        self.save()
        return self.candidates[candidate_id]

    def rollback_to(self, current_version: str, target_version: str) -> bool:
        """Rollback cost chain: deactivate current_version and restore target_version.

        After rollback:
        - current_version is marked ROLLED_BACK (no longer consumed by chain_matrix)
        - target_version is restored to ACTIVE (its components unchanged)
        - config weights are synced to target_version's signal weights

        Returns True on success, raises ValueError on error.
        """
        if current_version == target_version:
            raise ValueError(f"Cannot rollback: current and target are the same ({current_version})")

        models = self._cost_chain_models
        if target_version not in models:
            raise ValueError(f"Target version {target_version} not found in cost chain models")
        if current_version not in models:
            raise ValueError(f"Current version {current_version} not found in cost chain models")

        current = models[current_version]
        target = models[target_version]

        # Mark current version as ROLLED_BACK
        models[current_version] = current.model_copy(update={
            "status": "ROLLED_BACK",
        })

        # Restore target version to ACTIVE (its components remain unchanged)
        models[target_version] = target.model_copy(update={
            "status": "ACTIVE",
        })

        # Sync config weights to target version's signal weights
        weights = {
            component.related_sector: component.signal_weight
            for component in target.components
        }
        self._config = self._config.model_copy(update={"chain_cost_signal_weights": weights})

        self.audit_log.append(CostChainAudit(
            audit_id=f"audit-rollback-{current_version}-to-{target_version}",
            candidate_id="system-rollback",
            action="rolled_back",
            before_version=current_version,
            after_version=target_version,
            actor="user",
            created_at=_dt.now(),
            note=f"Rolled back {current_version} to {target_version}",
        ))
        self.save()
        return True

    def get_audit_log(self) -> list[CostChainAudit]:
        """Return all audit entries sorted by time descending."""
        return sorted(self.audit_log, key=lambda a: a.created_at, reverse=True)

    # ── Backtest run methods ──────────────────────────────────────────────

    def add_backtest_run(self, run: BacktestRun, result: BacktestResult | None = None) -> BacktestRun:
        """Persist a backtest run (and optional full result), enforcing MAX_BACKTEST_RUNS limit."""
        self.backtest_runs[run.run_id] = run
        if result is not None:
            self.backtest_results[run.run_id] = result
        # Enforce max count — evict oldest by created_at
        if len(self.backtest_runs) > MAX_BACKTEST_RUNS:
            sorted_runs = sorted(
                self.backtest_runs.values(),
                key=lambda r: r.created_at,
            )
            excess = len(sorted_runs) - MAX_BACKTEST_RUNS
            for r in sorted_runs[:excess]:
                self.backtest_runs.pop(r.run_id, None)
                self.backtest_results.pop(r.run_id, None)
        self.save()
        return run

    def list_backtest_runs(self) -> list[BacktestRun]:
        """Return all backtest runs sorted by creation time descending."""
        return sorted(
            self.backtest_runs.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )

    def get_backtest_run(self, run_id: str) -> BacktestRun | None:
        """Look up a backtest run by ID."""
        return self.backtest_runs.get(run_id)

    def get_backtest_result(self, run_id: str) -> BacktestResult | None:
        """Look up a full backtest result by run ID."""
        return self.backtest_results.get(run_id)


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
            "candidates": [item.model_dump(mode="json") for item in self.candidates.values()],
            "audit_log": [item.model_dump(mode="json") for item in self.audit_log],
            "backtest_runs": [item.model_dump(mode="json") for item in self.backtest_runs.values()],
            "backtest_results": [item.model_dump(mode="json") for item in self.backtest_results.values()],
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
        self.candidates = {
            item.candidate_id: item
            for item in (CostChainCandidate.model_validate(row) for row in payload.get("candidates", []))
        }
        self.audit_log = [
            CostChainAudit.model_validate(row) for row in payload.get("audit_log", [])
        ]
        self.backtest_runs = {
            item.run_id: item
            for item in (BacktestRun.model_validate(row) for row in payload.get("backtest_runs", []))
        }
        self.backtest_results = {
            item.run_id: item
            for item in (BacktestResult.model_validate(row) for row in payload.get("backtest_results", []))
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
