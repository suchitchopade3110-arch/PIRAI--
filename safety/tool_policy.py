from typing import Any, Dict, Mapping, Optional

from safety.taxonomy import AttackCategory, RiskLevel, SecuritySource

TOOL_POLICIES: Dict[str, Dict[str, Any]] = {
    "read_file": {"allowed_actions": {"read"}, "required_permission": "files:read", "risk_level": "MEDIUM"},
    "write_file": {"allowed_actions": {"write"}, "required_permission": "files:write", "risk_level": "HIGH"},
    "http_request": {"allowed_actions": {"get"}, "required_permission": "network:read", "risk_level": "HIGH"},
}


def authorize_tool_request(request: Optional[Mapping[str, Any]], trusted_permissions: Optional[set[str]] = None) -> Dict[str, Any]:
    if not request:
        return {"decision": "ALLOW", "tool_invoked": False, "source": SecuritySource.TOOL_REQUEST.value}
    name = str(request.get("name", ""))
    action = str(request.get("action", "")).lower()
    arguments = request.get("arguments", {})
    policy = TOOL_POLICIES.get(name)
    if not policy or action not in policy["allowed_actions"] or not isinstance(arguments, dict):
        return {"decision": "BLOCK", "category": AttackCategory.TOOL_ABUSE.value, "risk_level": RiskLevel.HIGH.value, "reason": "Unknown tool, disallowed action, or invalid arguments", "tool_invoked": False, "source": SecuritySource.TOOL_REQUEST.value}
    if policy["required_permission"] not in (trusted_permissions or set()):
        return {"decision": "BLOCK", "category": AttackCategory.TOOL_ABUSE.value, "risk_level": policy["risk_level"], "reason": "Trusted application permission is missing", "tool_invoked": False, "source": SecuritySource.TOOL_REQUEST.value}
    if any(key.lower() in {"password", "token", "api_key", "secret"} for key in arguments):
        return {"decision": "BLOCK", "category": AttackCategory.DATA_EXFILTRATION.value, "risk_level": RiskLevel.CRITICAL.value, "reason": "Sensitive arguments are not permitted", "tool_invoked": False, "source": SecuritySource.TOOL_REQUEST.value}
    return {"decision": "ALLOW", "risk_level": policy["risk_level"], "tool_invoked": False, "source": SecuritySource.TOOL_REQUEST.value}
