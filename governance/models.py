"""Typed governance records. Records contain metadata, never request content."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class PolicyVersion:
    policy_version: str
    review_threshold: float
    block_threshold: float
    zero_tolerance_threshold: float
    zero_tolerance_categories: tuple[str, ...]
    safety_classifier: str
    coding_model: str
    tool_policy_version: str
    created_at: str
    activated_at: str

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["zero_tolerance_categories"] = list(self.zero_tolerance_categories)
        return value


@dataclass(frozen=True)
class ReviewRecord:
    review_id: str
    prompt_id: Optional[str]
    audit_event_id: str
    original_decision: str
    stage: str
    risk_category: Optional[str]
    risk_level: str
    score: Optional[float]
    policy_version: str
    status: str
    reviewer_id: Optional[str]
    reviewer_decision: Optional[str]
    justification: Optional[str]
    created_at: str
    resolved_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OverrideRecord:
    override_id: str
    review_id: Optional[str]
    audit_event_id: str
    original_decision: str
    final_decision: str
    reviewer_id: str
    reason: str
    policy_version: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernanceSummary:
    total_security_decisions: int
    decision_counts: Dict[str, int]
    pending_reviews: int
    approved_reviews: int
    rejected_reviews: int
    override_count: int
    decisions_by_risk_category: Dict[str, int]
    decisions_by_policy_version: Dict[str, int]
    tool_authorization_denials: int
    human_reviewed_cases: int
    reviewer_resolution_rate: Optional[float]
    average_review_resolution_seconds: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
