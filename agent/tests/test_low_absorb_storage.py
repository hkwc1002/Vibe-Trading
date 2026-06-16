"""Tests for InMemoryLowAbsorbStorage and JsonLowAbsorbStorage roundtrip."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal

import pytest

from src.low_absorb.config import LowAbsorbConfig
from src.low_absorb.cost_chain.models import (
    CostChainAudit,
    CostChainCandidate,
    CostChainCandidateStatus,
)
from src.low_absorb.models import (
    CloseReport,
    CostChainComponent,
    FeishuNotificationResult,
    LowAbsorbSignal,
    ManualFill,
    ManualPosition,
    ManualTradePlan,
    NotificationType,
    PositionStatus,
    SignalStatus,
    TradePlanStatus,
)
from src.low_absorb.storage import InMemoryLowAbsorbStorage, JsonLowAbsorbStorage


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def _sample_signal(signal_id: str = "sig-601138-20260614") -> LowAbsorbSignal:
    return LowAbsorbSignal(
        signal_id=signal_id,
        trade_date=date(2026, 6, 14),
        stock_code="601138",
        stock_name="工业富联",
        branch_name="AI 服务器",
        grade="A",
        ma20_deviation_pct=Decimal("-0.032"),
        volume_ratio=Decimal("0.72"),
        lower_shadow_atr=Decimal("1.18"),
        reason="主线分支强，尾盘缩量回踩 MA20 附近",
        status=SignalStatus.CANDIDATE,
    )


def _sample_plan(plan_id: str = "plan-601138-20260614") -> ManualTradePlan:
    return ManualTradePlan(
        plan_id=plan_id,
        signal_id="sig-601138-20260614",
        trade_date=date(2026, 6, 14),
        stock_code="601138",
        stock_name="工业富联",
        entry_low=Decimal("18.60"),
        entry_high=Decimal("18.95"),
        stop_loss=Decimal("17.88"),
        planned_position_pct=Decimal("0.12"),
        max_risk_pct=Decimal("0.0035"),
        initial_risk_r=Decimal("1.0"),
        initial_risk_cny=Decimal("107.00"),
        open_stop_risk_cny=Decimal("107.00"),
        r_multiple=Decimal("0.00"),
        rationale="人工执行建议，仅用于用户自行判断。",
        manual_order_text="601138 工业富联，人工低吸区间 18.60-18.95，参考止损 17.88。",
        status=TradePlanStatus.RECOMMENDED,
    )


def _sample_fill(fill_id: str = "fill-601138-20260614") -> ManualFill:
    return ManualFill(
        fill_id=fill_id,
        plan_id="plan-601138-20260614",
        signal_id="sig-601138-20260614",
        stock_code="601138",
        stock_name="工业富联",
        actual_price=Decimal("18.78"),
        quantity=1000,
        fee=Decimal("5.00"),
        executed_at=datetime(2026, 6, 14, 14, 55),
    )


def _sample_position(position_id: str = "pos-601138-20260614") -> ManualPosition:
    return ManualPosition(
        position_id=position_id,
        plan_id="plan-601138-20260614",
        stock_code="601138",
        stock_name="工业富联",
        opened_at=datetime(2026, 6, 14, 14, 55),
        avg_cost=Decimal("18.78"),
        current_price=Decimal("18.80"),
        stop_loss=Decimal("17.88"),
        quantity=1000,
        position_pct=Decimal("0.12"),
        status=PositionStatus.ACTIVE_POSITION,
    )


def _sample_report(report_id: str = "close-20260614") -> CloseReport:
    return CloseReport(
        report_id=report_id,
        trade_date=date(2026, 6, 14),
        summary="2026-06-14 AI Low Absorb 收盘复盘",
        signals=[_sample_signal()],
        trade_plans=[_sample_plan()],
        positions=[_sample_position()],
        review_items=["复核人工成交回填"],
    )


def _sample_component(**overrides: object) -> CostChainComponent:
    base = {
        "component": "GPU (B200)",
        "cost_weight": Decimal("0.35"),
        "cost_increase_vs_previous_generation": Decimal("0.25"),
        "related_sector": "GPU/加速卡",
        "signal_weight": Decimal("0.90"),
        "data_source": "NVIDIA 官网",
        "source_type": "官方资料",
        "confidence": "high",
        "is_estimated": False,
        "as_of": date(2026, 6, 1),
    }
    base.update(overrides)
    return CostChainComponent(**base)


# ---------------------------------------------------------------------------
# InMemoryLowAbsorbStorage tests
# ---------------------------------------------------------------------------

class TestInMemoryStorage:
    """Roundtrip tests for InMemoryLowAbsorbStorage."""

    def test_seed_and_clear(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        signal = _sample_signal()
        plan = _sample_plan()
        fill = _sample_fill()
        position = _sample_position()

        storage.seed(signals=[signal], trade_plans=[plan], fills=[fill], positions=[position])
        assert len(storage.signals) == 1
        assert len(storage.trade_plans) == 1
        assert len(storage.fills) == 1
        assert len(storage.positions) == 1

        storage.clear()
        assert len(storage.signals) == 0
        assert len(storage.trade_plans) == 0
        assert len(storage.fills) == 0
        assert len(storage.positions) == 0
        assert len(storage.notifications) == 0
        assert len(storage.reports) == 0

    def test_config_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        config = storage.get_config()
        assert isinstance(config, LowAbsorbConfig)

        updated = storage.update_config({"min_market_turnover_cny": "600000000000"})
        assert updated.min_market_turnover_cny == Decimal("600000000000")

        # Verify read-back consistency
        same = storage.get_config()
        assert same.min_market_turnover_cny == Decimal("600000000000")

    def test_webhook_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        assert storage.get_webhook() is None

        storage.update_webhook("https://open.feishu.cn/hook/test")
        assert storage.get_webhook() == "https://open.feishu.cn/hook/test"

        storage.update_webhook(None)
        assert storage.get_webhook() is None

    def test_cost_chain_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        components = [_sample_component()]

        updated = storage.update_cost_chain_model("custom/manual", components)
        assert updated.version == "custom/manual"
        assert updated.is_editable is True
        assert len(updated.components) == 1

        models = storage.get_cost_chain_models()
        assert "custom/manual" in models
        assert models["custom/manual"].components[0].component == "GPU (B200)"

    def test_builtin_version_rejected(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        components = [_sample_component()]

        with pytest.raises(ValueError, match="only custom/manual"):
            storage.update_cost_chain_model("GB200 NVL72", components)

        with pytest.raises(ValueError, match="only custom/manual"):
            storage.update_cost_chain_model("GB300 NVL72", components)

    def test_notification_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        notif = FeishuNotificationResult(
            notification_type=NotificationType.NOTIFIER_TEST,
            idempotency_key="test-key",
            ok=False,
            sent=False,
            message="missing webhook",
        )
        storage.notifications[notif.idempotency_key] = notif
        assert storage.notifications["test-key"].ok is False
        assert storage.notifications["test-key"].message == "missing webhook"

    def test_report_roundtrip(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        report = _sample_report()
        storage.reports[report.report_id] = report

        loaded = storage.reports["close-20260614"]
        assert loaded.summary == "2026-06-14 AI Low Absorb 收盘复盘"
        assert len(loaded.signals) == 1
        assert len(loaded.review_items) == 1


# ---------------------------------------------------------------------------
# JsonLowAbsorbStorage tests
# ---------------------------------------------------------------------------

class TestJsonStorage:
    """Roundtrip tests for JsonLowAbsorbStorage."""

    def test_entities_roundtrip(self, tmp_path: object) -> None:
        path = tmp_path / "low_absorb_state.json"
        storage = JsonLowAbsorbStorage(path)

        signal = _sample_signal()
        plan = _sample_plan()
        fill = _sample_fill()
        position = _sample_position()
        report = _sample_report()

        storage.seed(signals=[signal], trade_plans=[plan], fills=[fill], positions=[position])
        storage.reports[report.report_id] = report
        storage.update_webhook("https://open.feishu.cn/hook/test")
        storage.update_config({"min_market_turnover_cny": "600000000000"})
        storage.save()

        # Reload from the same file — all entities should be present
        reloaded = JsonLowAbsorbStorage(path)
        assert len(reloaded.signals) == 1
        assert reloaded.signals["sig-601138-20260614"].stock_code == "601138"
        assert len(reloaded.trade_plans) == 1
        assert reloaded.trade_plans["plan-601138-20260614"].stock_code == "601138"
        assert len(reloaded.fills) == 1
        assert reloaded.fills["fill-601138-20260614"].stock_code == "601138"
        assert len(reloaded.positions) == 1
        assert reloaded.positions["pos-601138-20260614"].stock_code == "601138"
        assert len(reloaded.reports) == 1
        assert reloaded.reports["close-20260614"].trade_date == date(2026, 6, 14)
        assert reloaded.get_webhook() == "https://open.feishu.cn/hook/test"
        assert reloaded.get_config().min_market_turnover_cny == Decimal("600000000000")

    def test_corrupt_json_recovery(self, tmp_path: object) -> None:
        path = tmp_path / "corrupt.json"
        path.write_text("{invalid json content", encoding="utf-8")

        storage = JsonLowAbsorbStorage(path)
        assert len(storage.signals) == 0
        assert len(storage.trade_plans) == 0
        assert len(storage.fills) == 0
        assert len(storage.positions) == 0
        assert len(storage.reports) == 0
        assert len(storage.notifications) == 0

    def test_non_existent_file_loads_empty(self, tmp_path: object) -> None:
        path = tmp_path / "nonexistent.json"
        assert not path.exists()

        storage = JsonLowAbsorbStorage(path)
        assert len(storage.signals) == 0
        assert len(storage.trade_plans) == 0
        assert len(storage.fills) == 0
        assert len(storage.positions) == 0
        assert len(storage.reports) == 0
        assert len(storage.notifications) == 0

    def test_notifications_roundtrip_json(self, tmp_path: object) -> None:
        path = tmp_path / "notif_state.json"
        storage = JsonLowAbsorbStorage(path)

        result = FeishuNotificationResult(
            notification_type=NotificationType.CLOSE_REPORT,
            idempotency_key="notif-001",
            ok=True,
            sent=True,
            sent_at=datetime(2026, 6, 14, 15, 0),
            message="sent",
        )
        storage.notifications["notif-001"] = result
        storage.save()

        reloaded = JsonLowAbsorbStorage(path)
        assert len(reloaded.notifications) == 1
        assert reloaded.notifications["notif-001"].ok is True
        assert reloaded.notifications["notif-001"].message == "sent"


# ---------------------------------------------------------------------------
# Cost chain candidate model tests (RED phase — will fail until models exist)
# ---------------------------------------------------------------------------

class TestCostChainCandidateModel:
    def test_minimal_candidate(self) -> None:
        candidate = CostChainCandidate(
            candidate_id="cand-001",
            version="GB300 NVL72",
            source_type="manual",
            source_name="手动维护",
            confidence="medium",
            components=[_sample_component()],
            created_at=datetime(2026, 6, 15),
        )
        assert candidate.candidate_id == "cand-001"
        assert candidate.status == CostChainCandidateStatus.REVIEW_PENDING
        assert len(candidate.components) == 1

    def test_candidate_review_fields(self) -> None:
        candidate = CostChainCandidate(
            candidate_id="cand-002",
            version="GB200 NVL72",
            source_type="automatic",
            source_name="公开资料采集",
            confidence="low",
            components=[_sample_component()],
            created_at=datetime(2026, 6, 15),
            reviewed_at=datetime(2026, 6, 15, 10, 0),
            review_note="待补充来源",
        )
        assert candidate.reviewed_at is not None
        assert candidate.review_note == "待补充来源"

    def test_candidate_diff_summary(self) -> None:
        candidate = CostChainCandidate(
            candidate_id="cand-003",
            version="GB300 NVL72",
            source_type="fixture",
            source_name="测试数据",
            confidence="high",
            components=[_sample_component(cost_weight="0.50")],
            diff_summary=["GPU 权重从 0.42 升至 0.50"],
            created_at=datetime(2026, 6, 15),
        )
        assert len(candidate.diff_summary) == 1


class TestCostChainAuditModel:
    def test_minimal_audit(self) -> None:
        audit = CostChainAudit(
            audit_id="audit-001",
            candidate_id="cand-001",
            action="created",
            actor="collector",
            created_at=datetime(2026, 6, 15),
        )
        assert audit.audit_id == "audit-001"
        assert audit.before_version is None
        assert audit.after_version is None

    def test_audit_with_versions(self) -> None:
        audit = CostChainAudit(
            audit_id="audit-002",
            candidate_id="cand-001",
            action="activated",
            before_version="GB200 NVL72",
            after_version="GB300 NVL72 v2",
            actor="user",
            created_at=datetime(2026, 6, 15, 10, 0),
            note="审核通过，新版本生效",
        )
        assert audit.before_version == "GB200 NVL72"
        assert audit.after_version == "GB300 NVL72 v2"
        assert audit.note == "审核通过，新版本生效"


# ---------------------------------------------------------------------------
# Cost chain storage tests (RED phase — will fail until storage methods exist)
# ---------------------------------------------------------------------------

class TestCostChainStorage:
    def test_create_and_list_candidates(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        candidate = CostChainCandidate(
            candidate_id="cand-001",
            version="GB300 NVL72",
            source_type="manual",
            source_name="手动维护",
            confidence="medium",
            components=[_sample_component()],
            created_at=datetime(2026, 6, 15),
        )
        storage.create_candidate(candidate)
        candidates = storage.list_candidates()
        assert len(candidates) == 1
        assert candidates[0].candidate_id == "cand-001"

    def test_get_candidate_by_id(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        candidate = CostChainCandidate(
            candidate_id="cand-001",
            version="GB300 NVL72",
            source_type="manual",
            source_name="手动维护",
            confidence="medium",
            components=[_sample_component()],
            created_at=datetime(2026, 6, 15),
        )
        storage.create_candidate(candidate)
        loaded = storage.get_candidate("cand-001")
        assert loaded is not None
        assert loaded.candidate_id == "cand-001"

    def test_get_nonexistent_candidate(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        loaded = storage.get_candidate("nonexistent")
        assert loaded is None

    def test_update_candidate_status_to_approved(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        candidate = CostChainCandidate(
            candidate_id="cand-001",
            version="GB300 NVL72",
            source_type="manual",
            source_name="手动维护",
            confidence="medium",
            components=[_sample_component()],
            created_at=datetime(2026, 6, 15),
        )
        storage.create_candidate(candidate)
        updated = storage.update_candidate_status(
            "cand-001",
            CostChainCandidateStatus.APPROVED,
            review_note="来源可信",
        )
        assert updated.status == CostChainCandidateStatus.ACTIVE
        assert updated.review_note == "来源可信"

    def test_approve_candidate_deactivates_other_active_versions(self) -> None:
        """Approving a candidate marks other ACTIVE versions as ROLLED_BACK."""
        storage = InMemoryLowAbsorbStorage()
        # Precondition: GB200 NVL72 and GB300 NVL72 are both active (status=None)
        models_before = storage.get_cost_chain_models()
        assert models_before["GB200 NVL72"].status is None
        assert models_before["GB300 NVL72"].status is None

        # Create and approve a candidate for version "custom/manual"
        candidate = CostChainCandidate(
            candidate_id="cand-mutual",
            version="custom/manual",
            source_type="manual",
            source_name="手动维护",
            confidence="medium",
            components=[_sample_component()],
            created_at=datetime(2026, 6, 15),
        )
        storage.create_candidate(candidate)
        storage.update_candidate_status("cand-mutual", CostChainCandidateStatus.APPROVED)

        # GB200 and GB300 should now be ROLLED_BACK
        models_after = storage.get_cost_chain_models()
        assert models_after["GB200 NVL72"].status == "ROLLED_BACK"
        assert models_after["GB300 NVL72"].status == "ROLLED_BACK"
        # custom/manual should be ACTIVE
        assert models_after["custom/manual"].status == "ACTIVE"

    def test_update_candidate_status_to_rejected(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        candidate = CostChainCandidate(
            candidate_id="cand-001",
            version="GB300 NVL72",
            source_type="automatic",
            source_name="自动采集",
            confidence="low",
            components=[_sample_component()],
            created_at=datetime(2026, 6, 15),
        )
        storage.create_candidate(candidate)
        updated = storage.update_candidate_status(
            "cand-001",
            CostChainCandidateStatus.REJECTED,
            review_note="来源不可信",
        )
        assert updated.status == CostChainCandidateStatus.REJECTED

    def test_update_nonexistent_candidate_raises(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        with pytest.raises(ValueError, match="not found"):
            storage.update_candidate_status(
                "nonexistent",
                CostChainCandidateStatus.APPROVED,
            )

    def test_rollback_preserves_target_components(self) -> None:
        """rollback_to must NOT overwrite target_version's components."""
        storage = InMemoryLowAbsorbStorage()
        models = storage.get_cost_chain_models()
        gb200_gpu_weight = models["GB200 NVL72"].components[0].cost_weight
        gb300_gpu_weight = models["GB300 NVL72"].components[0].cost_weight
        assert gb200_gpu_weight != gb300_gpu_weight  # precond: versions differ

        result = storage.rollback_to("GB300 NVL72", "GB200 NVL72")
        assert result is True

        models_after = storage.get_cost_chain_models()
        assert models_after["GB200 NVL72"].components[0].cost_weight == gb200_gpu_weight
        # Also verify ALL components preserved, not just GPU
        assert len(models_after["GB200 NVL72"].components) == len(models["GB200 NVL72"].components)

    def test_rollback_deactivates_current_version(self) -> None:
        """rollback_to marks current_version as ROLLED_BACK."""
        storage = InMemoryLowAbsorbStorage()
        storage.rollback_to("GB300 NVL72", "GB200 NVL72")
        models = storage.get_cost_chain_models()
        assert models["GB300 NVL72"].status == "ROLLED_BACK"

    def test_rollback_keeps_target_version_active(self) -> None:
        """rollback_to keeps target_version ACTIVE."""
        storage = InMemoryLowAbsorbStorage()
        storage.rollback_to("GB300 NVL72", "GB200 NVL72")
        models = storage.get_cost_chain_models()
        # target_version should be ACTIVE (or None = backward compat ACTIVE)
        gb200_status = models["GB200 NVL72"].status
        assert gb200_status is None or gb200_status == "ACTIVE"

    def test_rollback_updates_config_weights(self) -> None:
        """rollback_to syncs config weights to target version's signal weights."""
        storage = InMemoryLowAbsorbStorage()
        models = storage.get_cost_chain_models()
        target_model = models["GB200 NVL72"]
        expected_weight = target_model.components[0].signal_weight

        storage.rollback_to("GB300 NVL72", "GB200 NVL72")

        config = storage.get_config()
        assert config.chain_cost_signal_weights.get("GPU/加速卡") == expected_weight

    def test_rollback_audit_before_after(self) -> None:
        """rollback_to records audit with correct before_version and after_version."""
        storage = InMemoryLowAbsorbStorage()
        storage.rollback_to("GB300 NVL72", "GB200 NVL72")
        audit_log = storage.get_audit_log()
        rollback_entries = [e for e in audit_log if e.action == "rolled_back"]
        assert len(rollback_entries) >= 1
        entry = rollback_entries[0]
        assert entry.before_version == "GB300 NVL72"
        assert entry.after_version == "GB200 NVL72"
        assert entry.actor is not None
        assert entry.created_at is not None

    def test_rollback_to_same_version_raises(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        with pytest.raises(ValueError, match="same"):
            storage.rollback_to("GB300 NVL72", "GB300 NVL72")

    def test_rollback_nonexistent_target_raises(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        with pytest.raises(ValueError, match="not found"):
            storage.rollback_to("GB300 NVL72", "NONEXISTENT")

    def test_audit_log_records_actions(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        candidate = CostChainCandidate(
            candidate_id="cand-001",
            version="GB300 NVL72",
            source_type="manual",
            source_name="手动维护",
            confidence="medium",
            components=[_sample_component()],
            created_at=datetime(2026, 6, 15),
        )
        storage.create_candidate(candidate)
        storage.update_candidate_status("cand-001", CostChainCandidateStatus.APPROVED)
        audit_log = storage.get_audit_log()
        assert len(audit_log) >= 2  # created + approved
        actions = [entry.action for entry in audit_log]
        assert "created" in actions
        assert "approved" in actions

    def test_audit_log_actor(self) -> None:
        storage = InMemoryLowAbsorbStorage()
        audit_log = storage.get_audit_log()
        if audit_log:
            assert all(hasattr(entry, "actor") for entry in audit_log)
            assert all(hasattr(entry, "created_at") for entry in audit_log)


class TestJsonStorageBackupRestore:
    """export_state / load_state roundtrip for JsonLowAbsorbStorage."""

    def test_export_state_creates_file(self, tmp_path) -> None:
        import tempfile

        fd, state_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(state_path)

        storage = JsonLowAbsorbStorage(state_path)
        storage.save()  # writes an empty state

        backup_dir = tmp_path / "backups"
        from src.low_absorb.deployment.backup import export_state

        result = export_state(storage, str(backup_dir))
        assert result.exists()
        assert result.stat().st_size > 0
        assert "low_absorb_state_" in result.name
        os.unlink(state_path)

    def test_load_state_roundtrip(self, tmp_path) -> None:
        import tempfile

        fd, state_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(state_path)

        # Write state with a test signal
        storage = JsonLowAbsorbStorage(state_path)
        signal = LowAbsorbSignal(
            signal_id="sig-backup-test",
            trade_date=date(2026, 6, 16),
            stock_code="601138",
            stock_name="工业富联",
            branch_name="AI 服务器",
            grade="A",
            ma20_deviation_pct=Decimal("-0.03"),
            volume_ratio=Decimal("0.70"),
            lower_shadow_atr=Decimal("1.00"),
            reason="test",
        )
        storage.signals[signal.signal_id] = signal
        storage.save()

        # Backup
        from src.low_absorb.deployment.backup import export_state, load_state

        backup_dir = tmp_path / "backups"
        backup_path = export_state(storage, str(backup_dir))

        # Clear and restore
        storage.signals.clear()
        assert len(storage.signals) == 0

        load_state(storage, str(backup_path))
        assert signal.signal_id in storage.signals
        restored = storage.signals[signal.signal_id]
        assert restored.stock_name == "工业富联"

        os.unlink(state_path)

    def test_load_state_rejects_invalid_json(self, tmp_path) -> None:
        import tempfile

        fd, state_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(state_path)

        storage = JsonLowAbsorbStorage(state_path)
        storage.save()

        invalid = tmp_path / "bad.json"
        invalid.write_text("not json", encoding="utf-8")

        from src.low_absorb.deployment.backup import load_state

        with pytest.raises(ValueError, match="validation failed"):
            load_state(storage, str(invalid))

        os.unlink(state_path)


class TestJsonStorageDirectLoadState:
    """Direct JsonLowAbsorbStorage.load_state() roundtrip and failure tests."""

    def test_load_state_direct_roundtrip(self, tmp_path) -> None:
        import tempfile

        fd, state_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(state_path)

        storage = JsonLowAbsorbStorage(state_path)
        signal = LowAbsorbSignal(
            signal_id="sig-direct",
            trade_date=date(2026, 6, 16),
            stock_code="601138",
            stock_name="工业富联",
            branch_name="AI 服务器",
            grade="A",
            ma20_deviation_pct=Decimal("-0.03"),
            volume_ratio=Decimal("0.70"),
            lower_shadow_atr=Decimal("1.00"),
            reason="test",
        )
        storage.signals[signal.signal_id] = signal
        storage.save()

        backup_path = tmp_path / "backup.json"
        storage.export_state(str(backup_path))
        assert backup_path.exists()

        storage.signals.clear()
        assert len(storage.signals) == 0

        storage.load_state(str(backup_path))
        assert signal.signal_id in storage.signals
        restored = storage.signals[signal.signal_id]
        assert restored.stock_name == "工业富联"

        os.unlink(state_path)

    def test_load_state_direct_rejects_invalid_json(self, tmp_path) -> None:
        import tempfile

        fd, state_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(state_path)

        storage = JsonLowAbsorbStorage(state_path)
        storage.save()

        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")

        with pytest.raises(ValueError, match="not valid JSON"):
            storage.load_state(str(bad))

        os.unlink(state_path)

    def test_load_state_fail_closed_leaves_current_state_unchanged(self, tmp_path) -> None:
        import tempfile

        fd, state_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(state_path)

        storage = JsonLowAbsorbStorage(state_path)
        signal = LowAbsorbSignal(
            signal_id="sig-safe",
            trade_date=date(2026, 6, 16),
            stock_code="601138",
            stock_name="工业富联",
            branch_name="AI 服务器",
            grade="A",
            ma20_deviation_pct=Decimal("-0.03"),
            volume_ratio=Decimal("0.70"),
            lower_shadow_atr=Decimal("1.00"),
            reason="test",
        )
        storage.signals[signal.signal_id] = signal
        storage.save()
        from pathlib import Path
        original_content = Path(state_path).read_bytes()

        bad = tmp_path / "bad.json"
        bad.write_text("{invalid", encoding="utf-8")

        with pytest.raises((ValueError, json.JSONDecodeError)):
            storage.load_state(str(bad))

        # Current state must be byte-for-byte unchanged
        assert Path(state_path).read_bytes() == original_content
        assert signal.signal_id in storage.signals

        os.unlink(state_path)
