"""Governance metrics derived only from persisted audit and lifecycle records."""

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config import AUDIT_LOG_PATH, GOVERNANCE_OVERRIDES_PATH, GOVERNANCE_REPORT_PATH
from governance.models import GovernanceSummary, ReviewStatus
from governance.override_manager import OverrideManager
from governance.policy_registry import get_active_policy
from governance.review_manager import ReviewManager
from governance.storage import read_jsonl


def build_governance_report(
    *, audit_path: Path = AUDIT_LOG_PATH, review_manager: Optional[ReviewManager] = None,
    override_manager: Optional[OverrideManager] = None,
) -> Dict[str, Any]:
    policy = get_active_policy()
    events = list(read_jsonl(Path(audit_path)))
    reviews = (review_manager or ReviewManager()).list_reviews()
    overrides = (override_manager or OverrideManager()).list_overrides()
    decisions = Counter(str(item.get("decision", "UNKNOWN")).upper() for item in events)
    for decision in ("ALLOW", "REVIEW", "BLOCK", "REDACT", "IGNORE"):
        decisions.setdefault(decision, 0)
    categories = Counter(str(item.get("category") or "UNCATEGORIZED") for item in events)
    versions = Counter(str(item.get("policy_version") or "LEGACY_UNVERSIONED") for item in events)
    resolved = [item for item in reviews if item.status != ReviewStatus.PENDING.value]
    durations = []
    for item in resolved:
        if item.resolved_at:
            try:
                durations.append((datetime.fromisoformat(item.resolved_at) - datetime.fromisoformat(item.created_at)).total_seconds())
            except ValueError:
                pass
    summary = GovernanceSummary(
        total_security_decisions=len(events), decision_counts=dict(sorted(decisions.items())),
        pending_reviews=sum(item.status == ReviewStatus.PENDING.value for item in reviews),
        approved_reviews=sum(item.status == ReviewStatus.APPROVED.value for item in reviews),
        rejected_reviews=sum(item.status == ReviewStatus.REJECTED.value for item in reviews),
        override_count=len(overrides), decisions_by_risk_category=dict(sorted(categories.items())),
        decisions_by_policy_version=dict(sorted(versions.items())),
        tool_authorization_denials=sum(item.get("stage") == "TOOL_POLICY" and item.get("decision") != "ALLOW" for item in events),
        human_reviewed_cases=len(resolved),
        reviewer_resolution_rate=round(len(resolved) / len(reviews) * 100, 2) if reviews else None,
        average_review_resolution_seconds=round(sum(durations) / len(durations), 3) if durations else None,
    )
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "active_policy": policy.to_dict(), "summary": summary.to_dict(),
        "data_quality": {
            "review_metrics_available": bool(reviews),
            "resolution_time_available": bool(durations),
            "note": None if reviews else "Insufficient review data exists to calculate reviewer performance metrics.",
        },
    }


def write_governance_report(path: Path = GOVERNANCE_REPORT_PATH, **kwargs: Any) -> Dict[str, Any]:
    report = build_governance_report(**kwargs)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    return report
