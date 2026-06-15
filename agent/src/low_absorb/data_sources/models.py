"""Pydantic models for data source quality tracking.

These models capture the full lifecycle of a multi-source data fetch:
- Individual source attempts (success/failure, latency, error details)
- Conflicts between sources on the same field
- Health status of each source (circuit breaker pattern)
- Combined multi-source fetch result with fail-closed state
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DataSourceAttempt(BaseModel):
    """Record of a single attempt to fetch data from one source."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(..., min_length=1)
    source_type: str = Field(..., min_length=1)
    started_at: datetime = Field(...)
    finished_at: datetime | None = None
    ok: bool = False
    latency_ms: int | None = Field(default=None, ge=0)
    error_code: str | None = None
    error_message: str | None = None
    returned_rows: int | None = Field(default=None, ge=0)


_SOURCE_SEVERITY = Literal["info", "warning", "critical"]


class DataConflict(BaseModel):
    """Field-level value conflict between multiple sources."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(..., min_length=1)
    values_by_source: dict[str, str | None] = Field(default_factory=dict)
    tolerance: Decimal | None = Field(default=None, ge=0)
    severity: _SOURCE_SEVERITY = "warning"


_CIRCUIT_STATE = Literal["CLOSED", "OPEN", "HALF_OPEN"]


class DataSourceHealth(BaseModel):
    """Health status of a single data source with circuit breaker state."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(..., min_length=1)
    enabled: bool = True
    health_score: Decimal = Field(default=Decimal("100"), ge=0, le=100)
    circuit_state: _CIRCUIT_STATE = "CLOSED"
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    cooldown_until: datetime | None = None
    consecutive_failures: int = Field(default=0, ge=0)


class MultiSourceFetchResult(BaseModel):
    """Combined result of a multi-source data fetch operation."""

    model_config = ConfigDict(extra="forbid")

    ok: bool = False
    selected_source: str | None = None
    fallback_used: bool = False
    attempts: list[DataSourceAttempt] = Field(default_factory=list)
    conflicts: list[DataConflict] = Field(default_factory=list)
    freshness_seconds: int | None = Field(default=None, ge=0)
    data: Any = None
    fail_closed_reason: str | None = None
