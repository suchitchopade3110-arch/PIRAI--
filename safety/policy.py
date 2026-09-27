from typing import Dict, Any, Optional
from config import (
    ZERO_TOLERANCE,
    ZERO_TOLERANCE_THRESHOLD,
    REVIEW_THRESHOLD,
    BLOCK_THRESHOLD,
)


def evaluate_scores(scores: Dict[str, float]) -> Dict[str, Any]:
    """
    Evaluates safety classifier scores against thresholds and zero-tolerance policies.

    Decision rules:
    - If any category in ZERO_TOLERANCE has score >= ZERO_TOLERANCE_THRESHOLD -> BLOCK
    - Otherwise, find the maximum score among non-OK categories:
      - score >= BLOCK_THRESHOLD -> BLOCK
      - score >= REVIEW_THRESHOLD -> REVIEW
      - else -> ALLOW
    """
    # -------------------------
    # ZERO-TOLERANCE
    # -------------------------
    for category in ZERO_TOLERANCE:
        score = scores.get(category, 0.0)
        if score >= ZERO_TOLERANCE_THRESHOLD:
            return {
                "decision": "BLOCK",
                "category": category,
                "score": round(score, 4),
                "reason": "ZERO_TOLERANCE",
            }

    # -------------------------
    # NORMAL HARMFUL CATEGORIES
    # -------------------------
    harmful_scores = {
        label: score
        for label, score in scores.items()
        if label != "OK"
    }

    if not harmful_scores:
        return {
            "decision": "ALLOW",
            "category": None,
            "score": 0.0,
        }

    category, score = max(
        harmful_scores.items(),
        key=lambda x: x[1]
    )

    if score >= BLOCK_THRESHOLD:
        decision = "BLOCK"
    elif score >= REVIEW_THRESHOLD:
        decision = "REVIEW"
    else:
        decision = "ALLOW"

    return {
        "decision": decision,
        "category": category,
        "score": round(score, 4),
    }
