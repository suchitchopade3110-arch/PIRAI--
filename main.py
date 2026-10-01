import sys
import argparse

# Ensure standard output uses UTF-8 encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import torch
from agent.qwen_agent import safe_coding_agent


def print_banner():
    device = "CUDA" if torch.cuda.is_available() else "CPU"
    gpu_info = f" ({torch.cuda.get_device_name(0)})" if torch.cuda.is_available() else ""
    print("=" * 60)
    print(f"AI SAFETY PIPELINE - AUTONOMOUS CODING AGENT [{device}{gpu_info}]")
    print("=" * 60)


def handle_interactive_session():
    print_banner()
    print("Type your coding prompt below. Type 'exit' or 'quit' to end.\n")

    while True:
        try:
            user_prompt = input("Enter your prompt: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting AI Safety Pipeline. Goodbye!")
            break

        if not user_prompt:
            continue

        if user_prompt.lower() in {"exit", "quit"}:
            print("\nExiting AI Safety Pipeline. Goodbye!")
            break

        print("\nProcessing through safety pipeline...\n")

        try:
            result = safe_coding_agent(user_prompt)
        except Exception as e:
            print("❌ An unexpected error occurred while processing the request.")
            print(f"Details: {e}")
            print("-" * 60)
            continue

        status = result.get("status")

        print("=" * 60)
        print("FINAL PIPELINE RESULT")
        print("=" * 60)
        print("Status:", status)

        # -------------------------
        # BLOCKED
        # -------------------------
        if status == "BLOCKED":
            print("Stage :", result.get("stage", "UNKNOWN"))
            reason = result.get("reason", {})

            if isinstance(reason, dict):
                category = reason.get("category", reason.get("matches", "N/A"))
                score = reason.get("score", "N/A")
                detail_reason = reason.get("reason", "Safety policy violation")

                print(f"Category: {category}")
                print(f"Score   : {score}")
                print(f"Reason  : {detail_reason}")
            else:
                print(f"Reason  : {reason}")

            print("\n❌ Request stopped by the safety pipeline.")

        # -------------------------
        # HUMAN REVIEW
        # -------------------------
        elif status == "HUMAN_REVIEW":
            print("Stage :", result.get("stage", "UNKNOWN"))
            reason = result.get("reason", {})

            if isinstance(reason, dict):
                print(f"Category: {reason.get('category', 'N/A')}")
                print(f"Score   : {reason.get('score', 'N/A')}")
            print("\n⚠️ Request flagged for HUMAN REVIEW.")
            print("Review ID:", result.get("review_id", "Unavailable"))
            print("Governance status:", result.get("governance_status", "PENDING"))

        # -------------------------
        # ALLOWED
        # -------------------------
        elif status == "ALLOWED":
            print("\n✅ Request passed all safety checks.")
            print("\nQWEN RESPONSE:")
            print("-" * 60)
            print(result.get("response", ""))

        # -------------------------
        # ERROR
        # -------------------------
        else:
            print("Stage :", result.get("stage", "UNKNOWN"))
            print("Reason:", result.get("reason", "Processing error"))

        if result.get("policy_version"):
            print("Policy:", result["policy_version"])
        if result.get("event_id"):
            print("Audit event:", result["event_id"])

        print("\n" + "=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="AI Safety Agent - Content moderation & guardrails for autonomous coding agents"
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run comprehensive safety benchmarks (JailbreakBench, PAIR, Zero-Tolerance) and generate acceptance report",
    )

    args = parser.parse_args()

    if args.evaluate:
        print_banner()
        print("Initiating full safety and compliance evaluation suite...")
        from evaluation.report import run_full_evaluation
        run_full_evaluation()
    else:
        handle_interactive_session()


if __name__ == "__main__":
    main()
