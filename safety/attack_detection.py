import re
from typing import Any, Dict, Iterable, List, Optional

from safety.normalization import inspection_variants
from safety.taxonomy import AttackCategory, RiskLevel, SecuritySource

MAX_HISTORY_MESSAGES = 6

PATTERNS = {
    AttackCategory.SYSTEM_PROMPT_EXTRACTION: [
        r"\b(reveal|show|print|repeat|tell me|return|expose)\b.{0,45}\b(system|developer|hidden|internal)\b.{0,25}\b(prompt|message|instruction|policy|context)",
        r"\bwhat (system |developer )?instructions (were|are) you given\b",
    ],
    AttackCategory.SAFETY_BYPASS: [
        r"\b(disable|bypass|turn off|skip|avoid|do not run|ignore)\b.{0,35}\b(safety|moderation|policy|filter|security check|restriction)",
    ],
    AttackCategory.ROLE_HIJACKING: [
        r"\b(you are now|act as|pretend (you are|to be)|enter)\b.{0,35}\b(unrestricted|developer mode|system administrator|no rules|unbound)",
        r"\b(no longer bound|free from)\b.{0,30}\b(rule|instruction|restriction|policy)",
    ],
    AttackCategory.PRIVILEGE_ESCALATION: [
        r"\b(i am|assume i am|treat me as|grant me|give me)\b.{0,30}\b(admin|administrator|root|developer privilege|authorized operator|elevated permission)",
    ],
    AttackCategory.DATA_EXFILTRATION: [
        r"\b(print|show|reveal|return|output|dump|list|send|expose)\b.{0,40}\b(api key|secret|token|password|environment variable|env var|private file|internal config|hidden context|credential)",
    ],
    AttackCategory.TOOL_ABUSE: [
        r"\b(call|run|invoke|execute|use)\b.{0,25}\b(tool|command|shell|api)\b.{0,35}\b(immediately|without permission|without approval|ignore permission|bypass)",
    ],
    AttackCategory.DIRECT_PROMPT_INJECTION: [
        r"\b(ignore|forget|disregard|override)\b.{0,35}\b(previous|prior|system|developer|original|all)\b.{0,25}\b(instruction|message|rule|policy|restriction)",
        r"\bfollow only (my|these|the user) instructions\b",
    ],
}

COMPACT_SIGNATURES = {
    AttackCategory.DIRECT_PROMPT_INJECTION: (
        "ignorepreviousinstructions",
        "ignoreallpreviousinstructions",
        "forgetallpriorrules",
        "overridesysteminstructions",
    ),
    AttackCategory.SYSTEM_PROMPT_EXTRACTION: ("revealsystemprompt", "showhiddeninstructions"),
    AttackCategory.SAFETY_BYPASS: ("disablesafety", "bypassmoderation", "turnofffilters"),
}

REASONS = {
    AttackCategory.DIRECT_PROMPT_INJECTION: "Attempt to override higher-priority instructions",
    AttackCategory.SYSTEM_PROMPT_EXTRACTION: "Attempt to expose protected instructions or hidden context",
    AttackCategory.ROLE_HIJACKING: "Attempt to replace the agent's governed role",
    AttackCategory.SAFETY_BYPASS: "Attempt to disable or bypass security controls",
    AttackCategory.TOOL_ABUSE: "Attempt to trigger a tool outside trusted authorization",
    AttackCategory.PRIVILEGE_ESCALATION: "Prompt text cannot grant trusted permissions",
    AttackCategory.DATA_EXFILTRATION: "Attempt to retrieve protected or sensitive data",
}


def _match(text: str) -> Optional[AttackCategory]:
    for category, patterns in PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return category
    compact = re.sub(r"[^a-z0-9]+", "", text)
    for category, signatures in COMPACT_SIGNATURES.items():
        if any(signature in compact for signature in signatures):
            return category
    return None


def _result(category: Optional[AttackCategory], source: SecuritySource, confidence: float = 0.0, reason: str = "No adversarial instruction detected") -> Dict[str, Any]:
    return {
        "detected": category is not None,
        "category": category.value if category else None,
        "risk_level": RiskLevel.HIGH.value if category else RiskLevel.LOW.value,
        "confidence": round(confidence, 2),
        "reason": reason,
        "source": source.value,
    }


def detect_attack(text: str, source: SecuritySource = SecuritySource.USER_INPUT) -> Dict[str, Any]:
    variants = inspection_variants(text)
    character_spaced = bool(re.search(r"(?<!\w)(?:[A-Za-z0-9]\s+){3,}[A-Za-z0-9](?!\w)", str(text or "")))
    for index, variant in enumerate(variants):
        category = _match(variant)
        if category:
            if index > 0 or character_spaced:
                return _result(AttackCategory.OBFUSCATED_JAILBREAK, source, 0.91, f"Obfuscated {category.value.lower().replace('_', ' ')} detected")
            if source == SecuritySource.RETRIEVED_CONTEXT:
                indirect = AttackCategory.CONTEXT_POISONING if category in {AttackCategory.TOOL_ABUSE, AttackCategory.DATA_EXFILTRATION} else AttackCategory.INDIRECT_PROMPT_INJECTION
                return _result(indirect, source, 0.94, "Untrusted context contains an instruction aimed at the agent")
            return _result(category, source, 0.95, REASONS[category])
    return _result(None, source)


def detect_multi_turn(prompt: str, history: Optional[Iterable[Any]] = None) -> Dict[str, Any]:
    recent: List[str] = []
    for item in list(history or [])[-MAX_HISTORY_MESSAGES:]:
        content = item.get("content", "") if isinstance(item, dict) else str(item)
        if content:
            recent.append(content)
    current = detect_attack(prompt)
    history_findings = [detect_attack(item, SecuritySource.CONVERSATION_HISTORY) for item in recent]
    suspicious_history = [item for item in history_findings if item["detected"]]
    trust_setup = any(re.search(r"\b(treat|consider|assume)\b.{0,25}\b(next|everything|messages?)\b.{0,20}\b(trusted|authorized|safe)\b", variant) for item in recent for variant in inspection_variants(item))
    if (current["detected"] and (suspicious_history or trust_setup)) or len(suspicious_history) >= 2:
        return _result(AttackCategory.MULTI_TURN_JAILBREAK, SecuritySource.CONVERSATION_HISTORY, 0.96, "Recent turns combine into an instruction-override attempt")
    return current
