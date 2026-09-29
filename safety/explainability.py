"""Safe, structured explanations for PIRAI security decisions.

This module deliberately explains policy outcomes, not model reasoning.  It must
never receive or reproduce raw prompts, model outputs, detector signatures, or
protected instructions.
"""

from datetime import datetime, timezone
import secrets
from typing import Any, Dict, Iterable, Mapping, Optional

from config import BLOCK_THRESHOLD, REVIEW_THRESHOLD, ZERO_TOLERANCE, ZERO_TOLERANCE_THRESHOLD


RISK_TEMPLATES = {
    "DIRECT_PROMPT_INJECTION": (
        "The request contains instructions attempting to override higher-priority application instructions.",
        "Remove the instruction-override request and submit only the legitimate task.",
    ),
    "INDIRECT_PROMPT_INJECTION": (
        "Untrusted reference material contains instructions aimed at changing the agent's behavior.",
        "Remove the embedded instructions or provide the material only as reference data.",
    ),
    "SYSTEM_PROMPT_EXTRACTION": (
        "The request attempts to expose protected system or developer instructions.",
        "Request the required functionality directly instead of asking for protected internal instructions.",
    ),
    "ROLE_HIJACKING": (
        "The request attempts to replace the agent's governed role or operating rules.",
        "Restate the legitimate task without role-replacement instructions.",
    ),
    "SAFETY_BYPASS": (
        "The request attempts to disable or bypass an application security control.",
        "Remove the bypass instructions and submit a policy-compliant request.",
    ),
    "OBFUSCATED_JAILBREAK": (
        "The request contains an encoded or disguised attempt to evade security controls.",
        "Submit the legitimate request in clear language without obfuscation.",
    ),
    "MULTI_TURN_JAILBREAK": (
        "Recent conversation turns combine into an attempt to override application instructions.",
        "Start a clean request that states only the legitimate task.",
    ),
    "CONTEXT_POISONING": (
        "Untrusted context contains content intended to manipulate agent or tool behavior.",
        "Remove the manipulative content and use a trusted reference source.",
    ),
    "TOOL_ABUSE": (
        "The requested tool action is not authorized by trusted application permissions.",
        "Request an approved tool action or obtain the required permission through the application.",
    ),
    "PRIVILEGE_ESCALATION": (
        "The request attempts to obtain permissions that were not granted by the application.",
        "Use the application's approved permission process before retrying the action.",
    ),
    "DATA_EXFILTRATION": (
        "The request or output may expose credentials, secrets, or other protected data.",
        "Remove sensitive data and retry using approved, non-sensitive inputs or outputs.",
    ),
    "UNKNOWN_ADVERSARIAL": (
        "The request exhibits adversarial behavior that cannot be safely categorized.",
        "Rephrase the request clearly and submit only the legitimate task.",
    ),
}

TRACE_DESCRIPTIONS = {
    ("INPUT", "FAIL"): "The request was empty or invalid, so processing stopped.",
    ("JAILBREAK_DETECTION", "PASS"): "No deterministic jailbreak pattern was detected.",
    ("JAILBREAK_DETECTION", "FAIL"): "A deterministic adversarial instruction pattern was detected.",
    ("CONTEXT_ANALYSIS", "PASS"): "The supplied reference context passed adversarial-content analysis.",
    ("CONTEXT_ANALYSIS", "IGNORED"): "Untrusted context was excluded after adversarial content was detected.",
    ("INPUT_MODERATION", "PASS"): "The input safety classifier did not exceed a review threshold.",
    ("INPUT_MODERATION", "REVIEW"): "The input safety classifier requires human review.",
    ("INPUT_MODERATION", "BLOCK"): "The input safety classifier exceeded a blocking policy threshold.",
    ("SAFETY_POLICY", "ALLOW"): "The input passed the configured safety policy.",
    ("SAFETY_POLICY", "REVIEW"): "The configured safety policy requires human review.",
    ("SAFETY_POLICY", "BLOCK"): "The configured safety policy blocked the input.",
    ("TOOL_POLICY", "ALLOW"): "The requested tool action was authorized by trusted permissions.",
    ("TOOL_POLICY", "BLOCK"): "The requested tool action was denied by the authorization policy.",
    ("QWEN_GENERATION", "RUN"): "The coding model was invoked after input checks passed.",
    ("QWEN_GENERATION", "ERROR"): "The coding model was invoked but generation did not complete.",
    ("OUTPUT_MODERATION", "PASS"): "The generated output passed safety classification.",
    ("OUTPUT_MODERATION", "REVIEW"): "The generated output requires human review.",
    ("OUTPUT_MODERATION", "BLOCK"): "The generated output exceeded a blocking policy threshold.",
    ("SENSITIVE_DATA_SCAN", "ALLOW"): "No restricted content was found by the output security scan.",
    ("SENSITIVE_DATA_SCAN", "REDACT"): "Potential sensitive data was found and the output was removed.",
    ("SENSITIVE_DATA_SCAN", "BLOCK"): "Restricted internal or unsafe content was found in the output.",
}


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _explanation_id() -> str:
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"EXP-{date}-{secrets.token_hex(3).upper()}"


def _threshold(decision: str, category: Optional[str], score: Optional[float]) -> Optional[float]:
    if category in ZERO_TOLERANCE and score is not None and score >= ZERO_TOLERANCE_THRESHOLD:
        return ZERO_TOLERANCE_THRESHOLD
    if decision == "BLOCK" and score is not None:
        return BLOCK_THRESHOLD
    if decision == "REVIEW" and score is not None:
        return REVIEW_THRESHOLD
    if decision == "ALLOW" and score is not None:
        return REVIEW_THRESHOLD
    return None


def _policy_why(decision: str, category: Optional[str], score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if category in ZERO_TOLERANCE and score >= ZERO_TOLERANCE_THRESHOLD:
        return "A zero-tolerance category met or exceeded its configured blocking threshold."
    if decision == "BLOCK":
        return "The highest harmful-content score met or exceeded the configured block threshold."
    if decision == "REVIEW":
        return "The highest harmful-content score met the configured review threshold but remained below the block threshold."
    if decision == "ALLOW":
        return "The highest harmful-content score remained below the configured review threshold."
    return None


def explain_trace(trace: Optional[Iterable[Mapping[str, Any]]]) -> list[Dict[str, str]]:
    """Convert executed raw trace events into safe, human-readable stages."""
    explained = []
    for event in trace or []:
        stage = str(event.get("stage", "UNKNOWN"))
        result = str(event.get("status", event.get("result", "UNKNOWN")))
        explained.append({
            "stage": stage,
            "result": result,
            "description": TRACE_DESCRIPTIONS.get(
                (stage, result), "The recorded security pipeline stage completed with the shown result."
            ),
        })
    return explained


def build_explanation(
    *,
    decision: str,
    detected_by: str,
    risk_category: Optional[str] = None,
    risk_level: Optional[str] = None,
    source: Optional[str] = None,
    confidence: Optional[float] = None,
    score: Optional[float] = None,
    policy_basis: Optional[str] = None,
    model_invoked: bool = False,
    tool_invoked: bool = False,
    trace: Optional[Iterable[Mapping[str, Any]]] = None,
    why: Optional[str] = None,
    recommended_action: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a public explanation from structured, non-sensitive metadata."""
    decision = str(_value(decision)).upper()
    category = _value(risk_category)
    template = RISK_TEMPLATES.get(category, (None, None))
    safe_why = why or template[0] or _policy_why(decision, category, score)
    if not safe_why:
        safe_why = {
            "ALLOW": "All executed security checks passed the configured policy.",
            "IGNORE": "Untrusted content was excluded so processing could continue safely.",
            "REDACT": "Potential sensitive content was removed before returning a response.",
            "ERROR": "Generation could not be completed after the security checks ran.",
            "BLOCK": "The request was stopped by an application security policy.",
            "REVIEW": "A security policy requires a human decision before processing can continue.",
        }.get(decision, "The application applied the recorded security decision.")
    action = recommended_action or template[1] or {
        "ALLOW": "No security action is required; continue with the returned response.",
        "IGNORE": "Review or replace the excluded untrusted context if it is needed for the task.",
        "REVIEW": "A reviewer should assess the flagged category before approving further processing.",
        "BLOCK": "Revise the request to comply with the stated policy and retry.",
        "REDACT": "Remove sensitive content and regenerate the response.",
        "ERROR": "Retry the request; contact an operator if generation continues to fail.",
    }.get(decision, "Review the recorded decision before continuing.")

    return {
        "explanation_id": _explanation_id(),
        "decision": decision,
        "risk_category": category,
        "risk_level": _value(risk_level) or {
            "ALLOW": "LOW", "IGNORE": "HIGH", "REVIEW": "MEDIUM",
            "BLOCK": "HIGH", "REDACT": "CRITICAL", "ERROR": "MEDIUM",
        }.get(decision),
        "source": _value(source) or "SYSTEM_POLICY",
        "detected_by": str(_value(detected_by)),
        "confidence": confidence,
        "score": score,
        "threshold": _threshold(decision, category, score),
        "why": safe_why,
        "policy_basis": policy_basis or "PIRAI security policy",
        "execution": {"model_invoked": bool(model_invoked), "tool_invoked": bool(tool_invoked)},
        "recommended_action": action,
        "trace": explain_trace(trace),
    }


def attach_explanation(
    response: Dict[str, Any],
    *,
    detected_by: str,
    finding: Optional[Mapping[str, Any]] = None,
    decision: Optional[str] = None,
    policy_basis: Optional[str] = None,
    why: Optional[str] = None,
    recommended_action: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Attach an explanation to an agent response without exposing its content."""
    finding = finding or {}
    status_decisions = {
        "ALLOWED": "ALLOW",
        "BLOCKED": "BLOCK",
        "HUMAN_REVIEW": "REVIEW",
        "REDACTED": "REDACT",
        "ERROR": "ERROR",
    }
    resolved_decision = decision or status_decisions.get(str(response.get("status")), "ERROR")
    if finding.get("reason") == "ZERO_TOLERANCE":
        detected_by = "ZERO_TOLERANCE_POLICY"
    response["explanation"] = build_explanation(
        decision=resolved_decision,
        detected_by=detected_by,
        risk_category=finding.get("category"),
        risk_level=finding.get("risk_level"),
        source=finding.get("source", source),
        confidence=finding.get("confidence", finding.get("score")),
        score=finding.get("score"),
        policy_basis=policy_basis,
        model_invoked=bool(response.get("model_invoked")),
        tool_invoked=bool(response.get("tool_invoked")),
        trace=response.get("trace"),
        why=why,
        recommended_action=recommended_action,
    )
    return response
