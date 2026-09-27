import json
from datetime import datetime, timezone
from typing import Optional, Any
from config import AUDIT_LOG_PATH, RESULTS_DIR


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
) -> None:
    """
    Appends safety audit entries to results/safety_audit.jsonl.
    Avoids logging raw prompt contents to preserve privacy.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    event = {
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
    }

    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"[Warning] Failed to write audit log: {e}")
