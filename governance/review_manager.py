"""Persistent, immutable-lifecycle human review queue."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import secrets
import threading
from typing import Any, Dict, List, Optional

from config import GOVERNANCE_REVIEWS_PATH
from governance.models import ReviewRecord, ReviewStatus
from governance.policy_registry import get_active_policy
from governance.storage import append_jsonl, read_jsonl

_REVIEW_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"


class ReviewValidationError(ValueError):
    pass


class ReviewNotFoundError(LookupError):
    pass


class ReviewAlreadyResolvedError(RuntimeError):
    pass


class ReviewManager:
    def __init__(self, path: Path = GOVERNANCE_REVIEWS_PATH) -> None:
        self.path = Path(path)

    def create_review(
        self, *, prompt_id: Optional[str], audit_event_id: str, stage: str,
        risk_category: Optional[str], risk_level: str, score: Optional[float],
        original_decision: str = "REVIEW", policy_version: Optional[str] = None,
    ) -> ReviewRecord:
        if not str(audit_event_id).strip():
            raise ReviewValidationError("audit_event_id is required")
        record = ReviewRecord(
            review_id=_id("REV"), prompt_id=prompt_id, audit_event_id=audit_event_id,
            original_decision=original_decision, stage=stage,
            risk_category=risk_category, risk_level=risk_level, score=score,
            policy_version=policy_version or get_active_policy().policy_version,
            status=ReviewStatus.PENDING.value, reviewer_id=None,
            reviewer_decision=None, justification=None, created_at=_now(), resolved_at=None,
        )
        append_jsonl(self.path, {"record_type": "REVIEW_CREATED", **record.to_dict()})
        return record

    def list_reviews(self, status: Optional[str] = None) -> List[ReviewRecord]:
        latest: Dict[str, Dict[str, Any]] = {}
        for item in read_jsonl(self.path):
            if item.get("review_id"):
                latest[item["review_id"]] = item
        records = [self._from_dict(item) for item in latest.values()]
        if status:
            records = [item for item in records if item.status == status.upper()]
        return sorted(records, key=lambda item: item.created_at, reverse=True)

    def get_review(self, review_id: str) -> ReviewRecord:
        match = next((item for item in self.list_reviews() if item.review_id == review_id), None)
        if match is None:
            raise ReviewNotFoundError(f"Unknown review ID: {review_id}")
        return match

    def resolve_review(self, review_id: str, *, reviewer_id: str, decision: str, justification: str) -> ReviewRecord:
        reviewer_id = str(reviewer_id or "").strip()
        justification = str(justification or "").strip()
        decision = str(decision or "").upper().strip()
        if not reviewer_id:
            raise ReviewValidationError("reviewer_id is required")
        if not justification:
            raise ReviewValidationError("justification is required")
        if decision not in {ReviewStatus.APPROVED.value, ReviewStatus.REJECTED.value}:
            raise ReviewValidationError("decision must be APPROVED or REJECTED")
        with _REVIEW_LOCK:
            current = self.get_review(review_id)
            if current.status != ReviewStatus.PENDING.value:
                raise ReviewAlreadyResolvedError(f"Review {review_id} is immutable after resolution")
            resolved = replace(
                current, status=decision, reviewer_id=reviewer_id,
                reviewer_decision=decision, justification=justification, resolved_at=_now(),
            )
            append_jsonl(self.path, {"record_type": "REVIEW_RESOLVED", **resolved.to_dict()})
            return resolved

    @staticmethod
    def _from_dict(item: Dict[str, Any]) -> ReviewRecord:
        fields = ReviewRecord.__dataclass_fields__
        return ReviewRecord(**{key: item.get(key) for key in fields})
