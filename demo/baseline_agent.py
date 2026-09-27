from typing import Any, Dict

from safety.audit import audit_log


def run_baseline(prompt: str, prompt_id: str, category: str) -> Dict[str, Any]:
    """Show that an unchecked prompt reaches generation without producing unsafe content."""
    result = {
        "prompt_id": prompt_id,
        "mode": "baseline",
        "model_invoked": True,
        "decision": "ALLOW" if category == "SAFE" else "VULNERABLE",
        "blocked_at": None,
        "category": category,
        "risk_score": None,
        "response": "Attack reached model / generation layer.",
        "trace": [
            {"stage": "JAILBREAK_DETECTION", "status": "SKIPPED"},
            {"stage": "INPUT_MODERATION", "status": "SKIPPED"},
            {"stage": "SAFETY_POLICY", "status": "SKIPPED"},
            {"stage": "GENERATION_BOUNDARY", "status": "REACHED"},
        ],
    }
    audit_log(
        stage="GENERATION_BOUNDARY",
        decision="REACHED",
        category=category,
        reason="Controlled demo; no unsafe generation performed",
        prompt_id=prompt_id,
        mode="baseline",
        model_invoked=True,
    )
    return result
