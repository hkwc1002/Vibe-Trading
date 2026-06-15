"""Cost chain candidate and audit models for semi-automated update workflow."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from ..models import CostChainComponent, LowAbsorbBaseModel


class CostChainCandidateStatus(str, Enum):
    """Status lifecycle: REVIEW_PENDING → APPROVED → ACTIVE, or → REJECTED.
    ACTIVE can later be ROLLED_BACK.
    """

    REVIEW_PENDING = "REVIEW_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACTIVE = "ACTIVE"
    ROLLED_BACK = "ROLLED_BACK"


class CostChainCandidate(LowAbsorbBaseModel):
    """A candidate cost chain version pending human review."""

    candidate_id: str
    version: str
    source_type: str  # automatic, manual, fixture
    source_name: str
    confidence: Literal["high", "medium", "low"]
    components: list[CostChainComponent]
    diff_summary: list[str] = []
    status: CostChainCandidateStatus = CostChainCandidateStatus.REVIEW_PENDING
    created_at: datetime
    reviewed_at: datetime | None = None
    review_note: str | None = None


class CostChainAudit(LowAbsorbBaseModel):
    """An immutable audit record for a cost chain action."""

    audit_id: str
    candidate_id: str
    action: str  # created, approved, rejected, activated, rolled_back
    before_version: str | None = None
    after_version: str | None = None
    actor: str  # user, collector, system
    created_at: datetime
    note: str | None = None
