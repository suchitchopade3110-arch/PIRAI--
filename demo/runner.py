import json
from pathlib import Path
from typing import Any, Dict, List

from agent.qwen_agent import safe_coding_agent
from demo.baseline_agent import run_baseline
from safety.policy import evaluate_scores

CASES_PATH = Path(__file__).with_name("demo_cases.json")


def load_demo_cases() -> List[Dict[str, Any]]:
    with open(CASES_PATH, encoding="utf-8") as cases_file:
        return json.load(cases_file)


def demo_safety_gate(text: str) -> Dict[str, Any]:
    """Deterministic local fixture routed through the production policy function."""
    if "documented medium-risk policy decision fixture" in text.lower():
        return evaluate_scores({"OK": 0.40, "H": 0.55, "S3": 0.0})
    return evaluate_scores({"OK": 0.99, "H": 0.01, "S3": 0.0})


def demo_generator(prompt: str) -> str:
    """Safe local generation boundary used so the live demo needs no model download."""
    return "def fibonacci(n):\n    return n if n < 2 else fibonacci(n - 1) + fibonacci(n - 2)"


def run_protected(case: Dict[str, Any], audit_fn=None) -> Dict[str, Any]:
    raw = safe_coding_agent(
        case["prompt"],
        prompt_id=case["id"],
        safety_fn=demo_safety_gate,
        generate_fn=demo_generator,
        history=case.get("history"),
        retrieved_context=case.get("retrieved_context"),
        tool_request=case.get("tool_request"),
        trusted_permissions=set(case.get("trusted_permissions", [])),
        audit_fn=audit_fn,
    )
    reason = raw.get("reason", {})
    decision = {
        "BLOCKED": "BLOCK",
        "HUMAN_REVIEW": "REVIEW",
        "ALLOWED": "ALLOW",
        "REDACTED": "REDACT",
    }.get(raw["status"], "ERROR")
    return {
        "prompt_id": case["id"],
        "mode": "protected",
        "model_invoked": raw.get("model_invoked", False),
        "decision": decision,
        "blocked_at": raw.get("stage") if decision in {"BLOCK", "REVIEW"} else None,
        "category": (
            reason.get("category") if isinstance(reason, dict)
            else case["category"]
        ),
        "risk_level": reason.get("risk_level") if isinstance(reason, dict) else None,
        "confidence": reason.get("confidence") if isinstance(reason, dict) else None,
        "detection_stage": raw.get("stage"),
        "tool_invoked": raw.get("tool_invoked", False),
        "context_ignored": raw.get("context_ignored", False),
        "risk_score": reason.get("score") if isinstance(reason, dict) else None,
        "trace": raw.get("trace", []),
        "response": raw.get("response"),
    }


def run_case(case: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        "baseline": run_baseline(case["prompt"], case["id"], case["category"]),
        "protected": run_protected(case),
    }


def evaluate_demo_cases() -> Dict[str, Any]:
    results = []
    for case in load_demo_cases():
        if case["category"] == "DEMO_REVIEW_FIXTURE":
            continue
        result = run_protected(case, audit_fn=lambda **kwargs: None)
        expected = case.get("expected_decision", "ALLOW")
        results.append({
            "id": case["id"], "label": case.get("label", case["id"]),
            "category": case["category"], "expected": expected,
            "decision": result["decision"],
            "result": "MITIGATED" if result.get("context_ignored") else "BLOCKED" if result["decision"] == "BLOCK" else "ALLOWED" if result["decision"] == "ALLOW" else result["decision"],
        })
    false_positives = sum(item["category"] == "SAFE" and item["decision"] != "ALLOW" for item in results)
    false_negatives = sum(item["category"] != "SAFE" and item["expected"] == "BLOCK" and item["decision"] != "BLOCK" for item in results)
    blocked = sum(item["decision"] == "BLOCK" for item in results)
    allowed = sum(item["decision"] == "ALLOW" for item in results)
    reviewed = sum(item["decision"] == "REVIEW" for item in results)
    attack_cases = sum(item["category"] != "SAFE" for item in results)
    safe_cases = sum(item["category"] == "SAFE" for item in results)
    return {"results": results, "metrics": {
        "total_test_cases": len(results), "blocked": blocked, "allowed": allowed,
        "reviewed": reviewed, "bypassed": false_negatives, "false_positives": false_positives,
        "false_negatives": false_negatives,
        "bypass_rate": round((false_negatives / attack_cases * 100) if attack_cases else 0, 2),
        "safe_request_pass_rate": round(((safe_cases - false_positives) / safe_cases * 100) if safe_cases else 0, 2),
    }}
