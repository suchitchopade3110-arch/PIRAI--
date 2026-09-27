import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from demo.runner import evaluate_demo_cases, load_demo_cases, run_case

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
RESULTS_DIR = ROOT / "results"


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
            })
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/demo":
            self.send_json({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
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


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8080), AppHandler)
    print("RAI Security dashboard: http://127.0.0.1:8080")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
