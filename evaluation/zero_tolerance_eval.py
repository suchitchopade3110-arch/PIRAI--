from typing import Dict, Any
from safety.policy import evaluate_scores


def evaluate_zero_tolerance() -> Dict[str, Any]:
    """
    Evaluates zero-tolerance policy enforcement and human review escalation
    using synthetic score vectors (avoiding storage of illegal or harmful material).
    """
    print("\n===============================")
    print("RUNNING ZERO-TOLERANCE & HUMAN REVIEW POLICY TEST")
    print("===============================")

    # Synthetic tests for zero-tolerance categories (e.g., S3 >= 0.30)
    zero_tolerance_tests = [
        {"OK": 0.01, "S3": 0.99},
        {"OK": 0.10, "S3": 0.80},
        {"OK": 0.30, "S3": 0.50},
    ]

    zt_results = []
    for scores in zero_tolerance_tests:
        result = evaluate_scores(scores)
        zt_results.append(result["decision"] == "BLOCK")

    zero_tolerance_bypasses = sum(not passed for passed in zt_results)

    # Test for human review escalation (e.g. 0.40 <= score < 0.70)
    review_test = {
        "OK": 0.40,
        "H": 0.55,
        "V": 0.10,
        "S": 0.05,
        "S3": 0.00,
    }

    review_result = evaluate_scores(review_test)
    human_review_enabled = (review_result["decision"] == "REVIEW")

    print(f"Zero-tolerance bypasses: {zero_tolerance_bypasses}")
    print(f"Human review: {'ENABLED' if human_review_enabled else 'FAILED'}")

    zt_passed = (zero_tolerance_bypasses == 0)
    hr_passed = human_review_enabled

    return {
        "zero_tolerance_bypasses": zero_tolerance_bypasses,
        "zero_tolerance_passed": zt_passed,
        "human_review_enabled": human_review_enabled,
        "human_review_passed": hr_passed,
    }
