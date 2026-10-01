import json
import os
import secrets
import threading
from datetime import datetime, timezone
from typing import Optional, Any
from config import AUDIT_LOG_PATH, RESULTS_DIR
from governance.policy_registry import get_active_policy

_AUDIT_LOCK = threading.RLock()


class AuditPersistenceError(RuntimeError):
    """Raised when a security event cannot be durably recorded."""


def new_event_id() -> str:
    return f"EVT-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"


def audit_log(
    stage: str,
    decision: str,
    category: Optional[str] = None,
    score: Optional[float] = None,
    reason: Optional[Any] = None,
    prompt_id: Optional[str] = None,
    mode: str = "protected",
    model_invoked: Optional[bool] = None,
    source: Optional[str] = None,
    risk_level: Optional[str] = None,
    confidence: Optional[float] = None,
    tool_invoked: Optional[bool] = None,
) -> str:
    """
    Appends safety audit entries to results/safety_audit.jsonl.
    Avoids logging raw prompt contents to preserve privacy.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    policy = get_active_policy()
    event = {
        "event_id": new_event_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "decision": decision,
        "category": category,
        "score": score,
        "reason": reason,
        "prompt_id": prompt_id,
        "mode": mode,
        "model_invoked": model_invoked,
        "tool_invoked": tool_invoked,
        "source": source,
        "risk_level": risk_level,
        "confidence": confidence,
        "policy_version": policy.policy_version,
        "safety_model": policy.safety_classifier,
        "coder_model": policy.coding_model,
        "tool_policy_version": policy.tool_policy_version,
    }

    try:
        with _AUDIT_LOCK:
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
                f.flush()
                os.fsync(f.fileno())
    except (OSError, TypeError, ValueError) as e:
        raise AuditPersistenceError(f"Failed to write audit log: {e}") from e
    return event["event_id"]
