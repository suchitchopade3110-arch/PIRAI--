import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from demo.runner import evaluate_demo_cases, load_demo_cases, run_case
from governance.governance_report import build_governance_report, write_governance_report
from governance.override_manager import OverrideManager, OverrideValidationError
from governance.policy_registry import get_active_policy
from governance.review_manager import (
    ReviewAlreadyResolvedError, ReviewManager, ReviewNotFoundError, ReviewValidationError,
)

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
RESULTS_DIR = ROOT / "results"
MAX_REQUEST_BYTES = 16_384


def governance_payload() -> Dict[str, Any]:
    reviews = ReviewManager().list_reviews()
    overrides = OverrideManager().list_overrides()
    report = build_governance_report()
    return {
        "policy": get_active_policy().to_dict(),
        "summary": report["summary"],
        "data_quality": report["data_quality"],
        "pending_reviews": [item.to_dict() for item in reviews if item.status == "PENDING"][:50],
        "recent_reviews": [item.to_dict() for item in reviews[:50]],
        "recent_overrides": [item.to_dict() for item in reversed(overrides[-50:])],
    }


def load_audit_events() -> list[Dict[str, Any]]:
    path = RESULTS_DIR / "safety_audit.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(events[-200:]))


def parse_acceptance_report() -> Dict[str, Any]:
    path = RESULTS_DIR / "acceptance_report.txt"
    if not path.exists():
        return {"available": False}
    text = path.read_text(encoding="utf-8", errors="replace")

    def value(pattern: str, cast=int):
        match = re.search(pattern, text, re.MULTILINE)
        return cast(match.group(1)) if match else None

    return {
        "available": True,
        "jailbreakbench": {
            "total": value(r"STANDARD HARMFUL CONTENT TEST\s+Total:\s*(\d+)"),
            "blocked": value(r"STANDARD HARMFUL CONTENT TEST[\s\S]*?Blocked:\s*(\d+)"),
            "bypassed": value(r"STANDARD HARMFUL CONTENT TEST[\s\S]*?Bypasses:\s*(\d+)"),
            "bypass_rate": value(r"JailbreakBench bypass rate:\s*([\d.]+)%", float),
        },
        "pair": {
            "total": value(r"ADVERSARIAL JAILBREAK TEST\s+Total attacks:\s*(\d+)"),
            "blocked": value(r"ADVERSARIAL JAILBREAK TEST[\s\S]*?Blocked:\s*(\d+)"),
            "bypassed": value(r"ADVERSARIAL JAILBREAK TEST[\s\S]*?Bypasses:\s*(\d+)"),
            "bypass_rate": value(r"PAIR bypass rate:\s*([\d.]+)%", float),
        },
        "zero_tolerance_bypasses": value(r"ZERO-TOLERANCE POLICY TEST[\s\S]*?Bypasses:\s*(\d+)"),
        "human_review": "ENABLED" if "HUMAN REVIEW ESCALATION\n\nStatus:\nENABLED" in text else "FAILED",
        "overall_pass": "ACCEPTANCE PASSED" in text,
    }


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/bootstrap":
            self.send_json({
                "cases": load_demo_cases(),
                "evaluations": parse_acceptance_report(),
                "audit_events": load_audit_events(),
                "security_evaluation": evaluate_demo_cases(),
                "governance": governance_payload(),
            })
            return
        if self.path == "/api/governance":
            self.send_json(governance_payload())
            return
        if self.path == "/api/reviews":
            self.send_json({"reviews": [item.to_dict() for item in ReviewManager().list_reviews()]})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.startswith("/api/reviews/"):
            self._resolve_review(self.path.removeprefix("/api/reviews/"))
            return
        if self.path == "/api/overrides":
            self._create_override()
            return
        if self.path == "/api/governance/report":
            self.send_json(write_governance_report())
            return
        if self.path != "/api/demo":
            self.send_json({"error": "Not found"}, 404)
            return
        try:
            payload = self._read_payload()
            case_id = str(payload.get("case_id", ""))
            prompt = str(payload.get("prompt", "")).strip()
            source = next((item for item in load_demo_cases() if item["id"] == case_id), None)
            if source is None or not prompt:
                self.send_json({"error": "Select a valid test case and provide an input."}, 400)
                return
            case = {**source, "prompt": prompt}
            self.send_json({"case": case, "result": run_case(case)})
        except Exception:
            self.send_json({
                "error": "The local security test could not run. Pre-generation controls remain unchanged."
            }, 500)

    def _read_payload(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("Invalid request size")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def _resolve_review(self, review_id: str) -> None:
        try:
            if not re.fullmatch(r"REV-\d{8}-[A-F0-9]{6}", review_id):
                raise ReviewNotFoundError("Unknown review ID")
            payload = self._read_payload()
            record = ReviewManager().resolve_review(
                review_id, reviewer_id=payload.get("reviewer_id", ""),
                decision=payload.get("decision", ""), justification=payload.get("justification", ""),
            )
            self.send_json({"review": record.to_dict()})
        except (ReviewValidationError, ValueError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except ReviewNotFoundError as exc:
            self.send_json({"error": str(exc)}, 404)
        except ReviewAlreadyResolvedError as exc:
            self.send_json({"error": str(exc)}, 409)
        except Exception:
            self.send_json({"error": "The review decision could not be persisted."}, 500)

    def _create_override(self) -> None:
        try:
            payload = self._read_payload()
            record = OverrideManager().create_override(
                audit_event_id=payload.get("audit_event_id", ""),
                review_id=payload.get("review_id"), original_decision=str(payload.get("original_decision", "")),
                final_decision=str(payload.get("final_decision", "")), reviewer_id=payload.get("reviewer_id", ""),
                reason=payload.get("reason", ""),
            )
            self.send_json({"override": record.to_dict()}, 201)
        except (OverrideValidationError, ValueError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception:
            self.send_json({"error": "The override could not be persisted."}, 500)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8080), AppHandler)
    print("RAI Security dashboard: http://127.0.0.1:8080")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
