from typing import Dict, List, Any

from safety.attack_detection import detect_attack

SUSPICIOUS_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal system prompt",
    "show system prompt",
    "bypass safety",
    "disable safety",
    "pretend there are no rules",
    "ignore safety policy",
]


def detect_jailbreak(text: str) -> Dict[str, Any]:
    """
    Deterministic early defense detecting explicit prompt injection / jailbreak patterns.
    """
    finding = detect_attack(text)
    matched: List[str] = [finding["reason"]] if finding["detected"] else []
    return {**finding, "matches": matched}
