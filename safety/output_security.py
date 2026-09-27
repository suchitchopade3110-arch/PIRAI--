import re
from typing import Any, Dict

from safety.taxonomy import AttackCategory, RiskLevel, SecuritySource

SECRET_PATTERNS = [
    re.compile(r"\b(?:api[_ -]?key|token|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/.]{8,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9]{12,}\b"),
]
INTERNAL_PATTERNS = [
    re.compile(r"\b(system prompt|developer message)\s*[:=]", re.IGNORECASE),
    re.compile(r"\b(ignore|override) (the )?(tool|security|policy) (gate|check|restriction)", re.IGNORECASE),
]


def scan_output(text: str) -> Dict[str, Any]:
    if any(pattern.search(str(text or "")) for pattern in SECRET_PATTERNS):
        return {"decision": "REDACT", "category": AttackCategory.DATA_EXFILTRATION.value, "risk_level": RiskLevel.CRITICAL.value, "reason": "Potential secret detected in model output", "source": SecuritySource.MODEL_OUTPUT.value}
    if any(pattern.search(str(text or "")) for pattern in INTERNAL_PATTERNS):
        return {"decision": "BLOCK", "category": AttackCategory.SYSTEM_PROMPT_EXTRACTION.value, "risk_level": RiskLevel.HIGH.value, "reason": "Restricted internal or tool-bypass content detected", "source": SecuritySource.MODEL_OUTPUT.value}
    return {"decision": "ALLOW", "category": None, "risk_level": RiskLevel.LOW.value, "source": SecuritySource.MODEL_OUTPUT.value}
