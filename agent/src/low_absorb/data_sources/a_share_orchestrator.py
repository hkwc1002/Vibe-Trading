"""A-share multi-source data orchestrator.

Manages source priorities, fallback chains, health tracking,
conflict detection, staleness checks, and production-mode fixture rejection.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Callable

from .health import HealthTracker
from .models import DataConflict, DataSourceAttempt, DataSourceHealth, MultiSourceFetchResult

_DEFAULT_SOURCE_ORDER = ["mootdx", "tencent", "baidu_sina", "eastmoney"]


def _default_adapter_factory(source_id: str) -> Any:
    from .a_share_adapters import BaiduSinaAdapter, EastmoneyAdapter, MootdxAdapter, TencentAdapter
    factories: dict[str, Callable] = {
        "mootdx": lambda: MootdxAdapter(),
        "tencent": lambda: TencentAdapter(),
        "baidu_sina": lambda: BaiduSinaAdapter(),
        "eastmoney": lambda: EastmoneyAdapter(),
    }
    f = factories.get(source_id)
    if f is None:
        raise ValueError(f"Unknown source: {source_id}")
    return f()


class AShareOrchestrator:
    """Manages multi-source A-share data access with health tracking and fetch orchestration."""

    def __init__(
        self,
        preferred_order: list[str] | None = None,
        adapter_factory: Callable[[str], Any] | None = None,
        failure_threshold: int = 3,
        cooldown_seconds: int = 60,
        conflict_tolerance_pct: Decimal | None = None,
        max_staleness_seconds: int | None = None,
        production_mode: bool = False,
    ) -> None:
        self.preferred_order = preferred_order or list(_DEFAULT_SOURCE_ORDER)
        self._adapter_factory = adapter_factory or _default_adapter_factory
        self._tracker = HealthTracker()
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._conflict_tolerance_pct = conflict_tolerance_pct
        self._max_staleness_seconds = max_staleness_seconds
        self._production_mode = production_mode
        self._last_fetch_result: MultiSourceFetchResult | None = None
        self._init_all()

    def _init_all(self) -> None:
        for source_id in self.preferred_order:
            self._tracker.get_or_create(source_id, failure_threshold=self._failure_threshold, cooldown_seconds=self._cooldown_seconds)

    # ── Health query ──

    def get_source_health(self, source_id: str) -> DataSourceHealth:
        cb = self._tracker.get_or_create(source_id, failure_threshold=self._failure_threshold, cooldown_seconds=self._cooldown_seconds)
        s = cb.status()
        return DataSourceHealth(source_id=s["source_id"], enabled=True, health_score=Decimal(str(s["health_score"])), circuit_state=s["circuit_state"], consecutive_failures=s["consecutive_failures"])

    def get_all_health(self) -> dict[str, DataSourceHealth]:
        return {sid: self.get_source_health(sid) for sid in self.preferred_order}

    def get_available_sources(self) -> list[str]:
        return [sid for sid in self.preferred_order if self._can_use(sid)]

    def _can_use(self, source_id: str) -> bool:
        cb = self._tracker.get_or_create(source_id, failure_threshold=self._failure_threshold, cooldown_seconds=self._cooldown_seconds)
        return cb.can_request()

    def record_source_success(self, source_id: str) -> None:
        self._tracker.record_success(source_id)

    def record_source_failure(self, source_id: str, error_code: str = "UNKNOWN") -> None:
        self._tracker.record_failure(source_id, error_code)

    def get_status_summary(self) -> dict:
        return self._tracker.summary()

    def get_all_health_dicts(self) -> dict[str, dict]:
        return self._tracker.all_statuses()

    def check_data_quality(self) -> tuple[bool, str | None]:
        """Check overall data quality state. Returns (ok: bool, reason: str | None).

        Combines source health checks with the last fetch result.
        Returns ok=False when the last fetch had conflicts, was stale,
        used fixture in production mode, or when no sources are available.
        """
        # Check last fetch result first (most specific)
        if self._last_fetch_result is not None:
            lr = self._last_fetch_result
            if not lr.ok:
                return False, lr.fail_closed_reason or "Last fetch failed (unknown reason)"
            if lr.conflicts:
                fields = ", ".join(c.field for c in lr.conflicts)
                return False, f"Data conflict detected on fields: {fields}"
            if lr.freshness_seconds is not None and self._max_staleness_seconds is not None:
                if lr.freshness_seconds > self._max_staleness_seconds:
                    return False, f"Data is stale: {lr.freshness_seconds}s > {self._max_staleness_seconds}s max"

        # Fall back to source availability check
        available = self.get_available_sources()
        if not available:
            return False, "No data sources available (all circuits open)"
        if self.preferred_order[0] not in available:
            return False, f"Preferred source '{self.preferred_order[0]}' is unavailable"

        return True, None

    # ── Multi-source fetch orchestration ──

    def fetch_quote(self, symbol: str) -> MultiSourceFetchResult:
        result = self._fetch("quote", symbol)
        self._last_fetch_result = result
        return result

    def fetch_kline(self, symbol: str, lookback: int = 20) -> MultiSourceFetchResult:
        result = self._fetch("kline", symbol, lookback)
        self._last_fetch_result = result
        return result

    def _fetch(self, method: str, symbol: str, lookback: int = 20) -> MultiSourceFetchResult:
        attempts: list[DataSourceAttempt] = []
        successes: list[tuple[str, Any, list[dict] | dict | None]] = []

        for source_id in self.preferred_order:
            if not self._can_use(source_id):
                continue
            started = datetime.now()
            try:
                adapter = self._adapter_factory(source_id)
                adap = adapter.fetch_quote(symbol) if method == "quote" else adapter.fetch_kline(symbol, lookback)
                finished = datetime.now()
                if adap.ok:
                    self._tracker.record_success(source_id)
                    successes.append((source_id, adap, adap.data))
                else:
                    self._tracker.record_failure(source_id, "FETCH_FAILED")
                attempts.append(DataSourceAttempt(
                    source_id=source_id, source_type=source_id, started_at=started, finished_at=finished,
                    ok=adap.ok, latency_ms=adap.latency_ms, returned_rows=adap.returned_rows,
                    error_message=None if adap.ok else (adap.error_message or "Unspecified error"),
                ))
            except Exception as exc:
                finished = datetime.now()
                self._tracker.record_failure(source_id, "EXCEPTION")
                attempts.append(DataSourceAttempt(
                    source_id=source_id, source_type=source_id, started_at=started, finished_at=finished,
                    ok=False, error_message=str(exc),
                ))

        if not successes:
            total = len(self.preferred_order)
            attempted = len(attempts)
            skipped = total - attempted
            return MultiSourceFetchResult(
                ok=False, selected_source=None, fallback_used=False, attempts=attempts,
                fail_closed_reason=f"All {total} sources failed: {attempted} attempted, {skipped} skipped due to circuit open",
            )

        best_source_id, best_adap, best_data = successes[0]
        fallback_used = successes[0][0] != self.preferred_order[0]

        # Staleness check
        if self._max_staleness_seconds is not None and best_adap.freshness_seconds is not None and best_adap.freshness_seconds > self._max_staleness_seconds:
            return MultiSourceFetchResult(
                ok=False, selected_source=best_source_id, fallback_used=fallback_used, attempts=attempts,
                fail_closed_reason=f"Data from {best_source_id} is stale: {best_adap.freshness_seconds}s > {self._max_staleness_seconds}s",
            )

        # Production mode: reject fixture fallback only (real source fallback is OK)
        if self._production_mode and fallback_used and getattr(best_adap, 'is_fixture', False):
            return MultiSourceFetchResult(
                ok=False, selected_source=best_source_id, fallback_used=fallback_used, attempts=attempts,
                fail_closed_reason=f"Production mode: fixture fallback rejected (source={best_source_id})",
            )

        # Conflict detection: compare key fields across successful sources
        conflicts: list[DataConflict] = []
        if self._conflict_tolerance_pct is not None and len(successes) >= 2:
            for field in ["close", "price", "open", "high", "low"]:
                values: dict[str, str | None] = {}
                for sid, adap, data in successes:
                    raw = data if isinstance(data, dict) else (data[-1] if isinstance(data, list) and data else {})
                    val = raw.get(field) if isinstance(raw, dict) else None
                    if val is not None:
                        values[sid] = str(val)
                if len(values) >= 2:
                    nums = []
                    for sid, v in values.items():
                        try:
                            nums.append((sid, Decimal(str(v))))
                        except Exception:
                            pass
                    if len(nums) >= 2:
                        mx = max(n[1] for n in nums)
                        mn = min(n[1] for n in nums)
                        if mn > 0 and (mx - mn) / mn > self._conflict_tolerance_pct:
                            conflicts.append(DataConflict(field=field, values_by_source=values, tolerance=self._conflict_tolerance_pct, severity="warning"))

        # Fail-closed on conflicts when tolerance is configured
        if conflicts:
            fields_str = ", ".join(c.field for c in conflicts)
            return MultiSourceFetchResult(
                ok=False, selected_source=best_source_id, fallback_used=fallback_used,
                attempts=attempts, conflicts=conflicts,
                freshness_seconds=best_adap.freshness_seconds,
                fail_closed_reason=f"Data conflict detected on fields: {fields_str}; values differ beyond tolerance",
            )

        return MultiSourceFetchResult(
            ok=True, selected_source=best_source_id, fallback_used=fallback_used,
            attempts=attempts, conflicts=conflicts,
            freshness_seconds=best_adap.freshness_seconds, data=best_data,
        )
