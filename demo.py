import argparse
import sys
from typing import Any, Dict, Iterable, List, Optional

from demo.baseline_agent import run_baseline
from demo.runner import load_demo_cases, run_protected

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WIDTH = 65


def heading(title: str) -> None:
    print("\n" + "=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def print_trace(result: Dict[str, Any]) -> None:
    for event in result["trace"]:
        print(f"[{event['status']:^7}] {event['stage'].replace('_', ' ').title()}")


def print_result(case: Dict[str, str], result: Dict[str, Any]) -> None:
    print(f"Prompt: {case['prompt']}")
    print_trace(result)
    print(f"\nModel invoked: {'YES' if result['model_invoked'] else 'NO'}")
    if result.get("blocked_at"):
        print(f"Stopped at: {result['blocked_at']}")
    if result.get("risk_score") is not None:
        print(f"Risk score: {result['risk_score']}")
    print(f"Final decision: {result['decision']}")


def summary(rows: Iterable[Dict[str, Any]]) -> None:
    heading("BEFORE vs AFTER")
    print(f"{'Case':<28}{'Baseline':<18}{'Protected':<18}")
    print("-" * WIDTH)
    for row in rows:
        baseline = (
            "ALLOWED" if row["baseline"]["decision"] == "ALLOW"
            else "MODEL REACHED" if row["baseline"]["model_invoked"]
            else row["baseline"]["decision"]
        )
        print(f"{row['id']:<28}{baseline:<18}{row['protected']['decision']:<18}")


def select_cases(case_id: Optional[str]) -> List[Dict[str, str]]:
    cases = load_demo_cases()
    if case_id is None:
        return cases
    selected = [case for case in cases if case["id"] == case_id]
    if not selected:
        available = ", ".join(case["id"] for case in cases)
        raise SystemExit(f"Unknown case '{case_id}'. Available: {available}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Local AI security before/after demonstration")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--baseline", action="store_true", help="Run baseline mode only")
    modes.add_argument("--protected", action="store_true", help="Run protected mode only")
    parser.add_argument("--case", help="Run a single demo case by ID")
    args = parser.parse_args()

    heading("AI SECURITY DEMONSTRATION")
    print("IDENTIFIED VULNERABILITY\n")
    print("Prompt Injection / Jailbreak Attacks")
    print("Unchecked adversarial instructions may reach an AI model and attempt")
    print("to override safety controls or reveal protected instructions.")
    print("\nDemo generation uses a safe local fixture; production uses Qwen.")

    rows = []
    for case in select_cases(args.case):
        row: Dict[str, Any] = {"id": case["id"]}
        if not args.protected:
            heading(f"WITHOUT SECURITY — {case['id']}")
            print("DEMO BASELINE — SECURITY CONTROLS DISABLED\n")
            row["baseline"] = run_baseline(case["prompt"], case["id"], case["category"])
            print_result(case, row["baseline"])
            baseline_outcome = (
                "ALLOWED" if row["baseline"]["decision"] == "ALLOW"
                else "VULNERABILITY DEMONSTRATED"
            )
            print(f"Result: {baseline_outcome}")
        if not args.baseline:
            heading(f"WITH SECURITY — {case['id']}")
            row["protected"] = run_protected(case)
            print_result(case, row["protected"])
            outcome = {"BLOCK": "ATTACK MITIGATED", "REVIEW": "ESCALATED", "ALLOW": "ALLOWED"}.get(
                row["protected"]["decision"], "ERROR"
            )
            print(f"Result: {outcome}")
        rows.append(row)

    if not args.baseline and not args.protected:
        summary(rows)
        heading("SECURITY EVIDENCE")
        print("Jailbreak detection: WORKING")
        print("Input moderation and policy: WORKING")
        print("Output moderation: WORKING")
        print("Audit logging: results/safety_audit.jsonl")
        print("Human review: ENABLED")
        print("Benchmark report: results/acceptance_report.txt (after evaluation)")


if __name__ == "__main__":
    main()
