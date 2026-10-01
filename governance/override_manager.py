"""Append-only manual override history; automated decisions are never mutated."""

from datetime import datetime, timezone
from pathlib import Path
import secrets
from typing import List, Optional

from config import AUDIT_LOG_PATH, GOVERNANCE_OVERRIDES_PATH
from governance.models import OverrideRecord
from governance.policy_registry import get_active_policy
from governance.storage import append_jsonl, read_jsonl
from governance.review_manager import ReviewManager, ReviewNotFoundError


class OverrideValidationError(ValueError):
    pass


class OverrideManager:
    def __init__(self, path: Path = GOVERNANCE_OVERRIDES_PATH, audit_path: Path = AUDIT_LOG_PATH,
                 review_manager: Optional[ReviewManager] = None) -> None:
        self.path = Path(path)
        self.audit_path = Path(audit_path)
        self.review_manager = review_manager or ReviewManager()

    def create_override(
        self, *, audit_event_id: str, original_decision: str, final_decision: str,
        reviewer_id: str, reason: str, review_id: Optional[str] = None,
        policy_version: Optional[str] = None,
    ) -> OverrideRecord:
        reviewer_id, reason = str(reviewer_id or "").strip(), str(reason or "").strip()
        original_decision = str(original_decision or "").upper().strip()
        final_decision = str(final_decision or "").upper().strip()
        if not reviewer_id or not reason:
            raise OverrideValidationError("reviewer_id and reason are required")
        if not str(audit_event_id or "").strip():
            raise OverrideValidationError("audit_event_id is required")
        if original_decision not in {"BLOCK", "REVIEW"} or final_decision not in {"ALLOW", "BLOCK"}:
            raise OverrideValidationError("invalid original or final decision")
        source = next((item for item in read_jsonl(self.audit_path)
                       if item.get("event_id") == audit_event_id), None)
        if source is None:
            raise OverrideValidationError("audit_event_id does not reference an existing event")
        if str(source.get("decision", "")).upper() != original_decision:
            raise OverrideValidationError("original_decision does not match the automated event")
        if review_id:
            try:
                review = self.review_manager.get_review(review_id)
            except ReviewNotFoundError as exc:
                raise OverrideValidationError("review_id does not reference an existing review") from exc
            if review.audit_event_id != audit_event_id:
                raise OverrideValidationError("review_id and audit_event_id do not match")
        now = datetime.now(timezone.utc)
        record = OverrideRecord(
            override_id=f"OVR-{now:%Y%m%d}-{secrets.token_hex(3).upper()}",
            review_id=review_id, audit_event_id=audit_event_id,
            original_decision=original_decision, final_decision=final_decision,
            reviewer_id=reviewer_id, reason=reason,
            policy_version=policy_version or get_active_policy().policy_version,
            timestamp=now.isoformat(),
        )
        append_jsonl(self.path, record.to_dict())
        return record

    def list_overrides(self) -> List[OverrideRecord]:
        return [OverrideRecord(**item) for item in read_jsonl(self.path)]
