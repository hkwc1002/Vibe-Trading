"""Production configuration validator for the Low Absorb module.

Validates runtime environment for production readiness before the
application accepts external traffic.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from ..config import LowAbsorbConfig
from ..cost_chain.models import CostChainCandidateStatus
from ..storage import LowAbsorbRepository


class ReadinessFailure:
    """A single readiness check outcome with a safe, non-revealing detail string."""

    name: str
    ok: bool
    detail: str

    def __init__(self, *, name: str, ok: bool, detail: str) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail


class ReadinessResult:
    """Aggregated production readiness result."""

    ready: bool
    failures: list[ReadinessFailure]

    def __init__(self, *, ready: bool, failures: list[ReadinessFailure] | None = None) -> None:
        self.ready = ready
        self.failures = failures or []


def _check_storage_writable(storage: LowAbsorbRepository) -> ReadinessFailure:
    """Verify the storage path can be written to.

    Returns ``ok=True`` with a generic ``"ok"`` detail when writable,
    or ``ok=False`` with ``"storage_not_writable"`` otherwise.
    """
    import json
    import tempfile

    from ..storage import JsonLowAbsorbStorage

    if not isinstance(storage, JsonLowAbsorbStorage):
        # InMemory storage is always writable in-process
        return ReadinessFailure(name="storage", ok=True, detail="ok")

    try:
        path = storage.path
        path.parent.mkdir(parents=True, exist_ok=True)
        # Probe-write a tiny temp file next to the real state file
        probe = path.parent / ".readiness_probe"
        probe.write_text(json.dumps({"probe": True}), encoding="utf-8")
        probe.unlink(missing_ok=True)
        return ReadinessFailure(name="storage", ok=True, detail="ok")
    except OSError:
        return ReadinessFailure(name="storage", ok=False, detail="storage_not_writable")


def _check_api_auth_key() -> ReadinessFailure:
    """Verify ``API_AUTH_KEY`` is set (for non-loopback remote access).

    Only returns ``configured`` or ``missing`` — never the key value itself.
    """
    key = os.environ.get("API_AUTH_KEY")
    if key:
        return ReadinessFailure(name="api_auth_key", ok=True, detail="configured")
    return ReadinessFailure(name="api_auth_key", ok=False, detail="missing")


def _check_fixture_fallback(config: LowAbsorbConfig) -> ReadinessFailure:
    """When ``data_production_mode`` is True, ``enable_fixture_fallback`` must be False.

    Returns ``ok`` when production mode is off or fixture fallback is disabled;
    returns ``fixture_fallback_forbidden`` when production mode is on and
    fixture fallback is still enabled.
    """
    if config.data_production_mode and config.enable_fixture_fallback:
        return ReadinessFailure(
            name="fixture_fallback",
            ok=False,
            detail="fixture_fallback_forbidden",
        )
    return ReadinessFailure(name="fixture_fallback", ok=True, detail="ok")


def _check_cost_chain_active(storage: LowAbsorbRepository) -> ReadinessFailure:
    """At least one cost-chain version must be ACTIVE (or None / ACTIVE status).

    A missing active chain means signal ranking cannot rely on cost data.
    """
    models = storage.get_cost_chain_models()
    active_versions = [
        v
        for v in models.values()
        if v.status is None or v.status == "ACTIVE"
    ]
    if active_versions:
        return ReadinessFailure(name="cost_chain", ok=True, detail="ok")
    return ReadinessFailure(name="cost_chain", ok=False, detail="no_active_version")


def _check_data_source(config: LowAbsorbConfig) -> ReadinessFailure:
    """Check data source readiness based on config mode.

    - In ``data_production_mode`` the provider must **not** be ``"fixture"``
      (only real or auto are acceptable).
    - Outside production mode, fixture-only is allowed — but the response
      still reflects it so the operator knows there is no real data.
    """
    if config.data_provider_mode == "fixture":
        if config.data_production_mode:
            return ReadinessFailure(name="data_source", ok=False, detail="fixture_only_with_production_mode")
        return ReadinessFailure(name="data_source", ok=True, detail="fixture_only")
    return ReadinessFailure(name="data_source", ok=True, detail="ok")


def _check_feishu_status(storage: LowAbsorbRepository) -> ReadinessFailure:
    """Check whether a Feishu webhook has been configured.

    Only returns ``configured`` or ``missing`` — never the webhook value.
    """
    webhook = storage.get_webhook() or os.getenv("LOW_ABSORB_FEISHU_WEBHOOK")
    if webhook:
        return ReadinessFailure(name="feishu", ok=True, detail="configured")
    return ReadinessFailure(name="feishu", ok=False, detail="missing")


_CHECKS: list[Callable[..., ReadinessFailure]] = [
    _check_storage_writable,
    _check_api_auth_key,
    _check_fixture_fallback,
    _check_data_source,
    _check_cost_chain_active,
    _check_feishu_status,
]


def validate_production_readiness(
    storage: LowAbsorbRepository,
    *,
    config: LowAbsorbConfig | None = None,
) -> ReadinessResult:
    """Run all production readiness checks and return an aggregated result.

    *storage* is the active Low Absorb repository.
    *config* — if omitted, ``storage.get_config()`` is used.
    """
    resolved_config = storage.get_config() if config is None else config
    failures: list[ReadinessFailure] = []

    for check in _CHECKS:
        if check in (_check_fixture_fallback, _check_data_source):
            result = check(resolved_config)  # type: ignore[arg-type]
        elif check in (_check_api_auth_key,):
            result = check()
        else:
            result = check(storage)
        if not result.ok:
            failures.append(result)

    return ReadinessResult(ready=len(failures) == 0, failures=failures)
