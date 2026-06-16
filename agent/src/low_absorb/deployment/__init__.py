"""Production-deployment utilities for the Low Absorb module."""

from __future__ import annotations

from .config_validator import ReadinessFailure, ReadinessResult, validate_production_readiness

__all__ = [
    "ReadinessFailure",
    "ReadinessResult",
    "validate_production_readiness",
]
