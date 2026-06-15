"""Circuit breaker and health tracking for multi-source data access."""

from __future__ import annotations

import time as time_module
from decimal import Decimal
from typing import Literal

_CircuitState = Literal["CLOSED", "OPEN", "HALF_OPEN"]
_HEALTH_DECAY = Decimal("20")
_HEALTH_RECOVERY = Decimal("5")
_HEALTH_MIN = Decimal("0")
_HEALTH_MAX = Decimal("100")
_FAILURE_THRESHOLD_DEFAULT = 3
_COOLDOWN_SECONDS_DEFAULT = 60


class CircuitBreaker:
    """Per-source circuit breaker with health scoring.

    State machine:
      CLOSED -> (failure_threshold reached) -> OPEN -> (cooldown expired) -> HALF_OPEN
      HALF_OPEN -> (success) -> CLOSED
      HALF_OPEN -> (failure) -> OPEN
    """

    def __init__(
        self,
        source_id: str,
        *,
        failure_threshold: int = _FAILURE_THRESHOLD_DEFAULT,
        cooldown_seconds: int = _COOLDOWN_SECONDS_DEFAULT,
    ) -> None:
        self.source_id = source_id
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state: _CircuitState = "CLOSED"
        self.health_score: Decimal = _HEALTH_MAX
        self.consecutive_failures: int = 0
        self.last_success_at: float | None = None
        self.last_failure_at: float | None = None
        self.cooldown_until: float | None = None

    def can_request(self) -> bool:
        """Check if a request can be made to this source.

        Transitions OPEN -> HALF_OPEN when cooldown has expired.
        """
        now = time_module.time()

        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            if self.cooldown_until is None or now >= self.cooldown_until:
                self.state = "HALF_OPEN"
                return True
            return False

        return True  # HALF_OPEN

    def record_success(self) -> None:
        """Record a successful fetch and improve health."""
        self.consecutive_failures = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
        self.health_score = min(_HEALTH_MAX, self.health_score + _HEALTH_RECOVERY)
        self.last_success_at = time_module.time()
        self.cooldown_until = None

    def record_failure(self, error_code: str = "UNKNOWN") -> None:
        """Record a failed fetch and degrade health."""
        self.consecutive_failures += 1
        self.last_failure_at = time_module.time()
        self.health_score = max(_HEALTH_MIN, self.health_score - _HEALTH_DECAY)

        if self.state == "HALF_OPEN":
            self.state = "OPEN"
            self.cooldown_until = time_module.time() + self.cooldown_seconds
        elif self.state != "OPEN" and self.consecutive_failures >= self.failure_threshold:
            self.state = "OPEN"
            self.cooldown_until = time_module.time() + self.cooldown_seconds

    def status(self) -> dict:
        """Return a snapshot of current health state."""
        return {
            "source_id": self.source_id,
            "circuit_state": self.state,
            "health_score": float(self.health_score),
            "consecutive_failures": self.consecutive_failures,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "cooldown_until": self.cooldown_until,
        }

    @property
    def is_healthy(self) -> bool:
        return self.state != "OPEN" and self.health_score >= _HEALTH_MIN


class HealthTracker:
    """Manages multiple circuit breakers and provides aggregated health views."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        source_id: str,
        *,
        failure_threshold: int = _FAILURE_THRESHOLD_DEFAULT,
        cooldown_seconds: int = _COOLDOWN_SECONDS_DEFAULT,
    ) -> CircuitBreaker:
        if source_id not in self._breakers:
            self._breakers[source_id] = CircuitBreaker(
                source_id=source_id,
                failure_threshold=failure_threshold,
                cooldown_seconds=cooldown_seconds,
            )
        return self._breakers[source_id]

    def record_success(self, source_id: str) -> dict | None:
        breaker = self._breakers.get(source_id)
        if breaker is None:
            return None
        breaker.record_success()
        return breaker.status()

    def record_failure(self, source_id: str, error_code: str = "UNKNOWN") -> dict | None:
        breaker = self.get_or_create(source_id)
        breaker.record_failure(error_code)
        return breaker.status()

    def all_statuses(self) -> dict[str, dict]:
        return {sid: breaker.status() for sid, breaker in self._breakers.items()}

    def summary(self) -> dict:
        healthy = degraded = unhealthy = 0
        for breaker in self._breakers.values():
            if breaker.health_score >= Decimal("80"):
                healthy += 1
            elif breaker.health_score >= Decimal("40"):
                degraded += 1
            else:
                unhealthy += 1
        return {
            "total_sources": len(self._breakers),
            "healthy_count": healthy,
            "degraded_count": degraded,
            "unhealthy_count": unhealthy,
        }
