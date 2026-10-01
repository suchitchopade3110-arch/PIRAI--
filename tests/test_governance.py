import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.qwen_agent import safe_coding_agent
from governance.governance_report import build_governance_report
from governance.override_manager import OverrideManager, OverrideValidationError
from governance.policy_registry import get_active_policy
from governance.review_manager import (
    ReviewAlreadyResolvedError, ReviewManager, ReviewNotFoundError, ReviewValidationError,
)
from governance.storage import GovernancePersistenceError
from safety.audit import audit_log
from safety.explainability import build_explanation
from safety.policy import evaluate_scores


def review_gate(_text):
    return evaluate_scores({"OK": 0.4, "H": 0.55})


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.audit_path = root / "audit.jsonl"
        self.reviews = ReviewManager(root / "reviews.jsonl")
        self.overrides = OverrideManager(
            root / "overrides.jsonl", self.audit_path, self.reviews,
        )

    def tearDown(self):
        self.temp.cleanup()

    def audit(self, **values):
        with patch("safety.audit.AUDIT_LOG_PATH", self.audit_path), patch("safety.audit.RESULTS_DIR", self.audit_path.parent):
            return audit_log(**values)

    def create_review(self):
        event_id = self.audit(
            stage="INPUT", decision="REVIEW", category="H", score=0.55,
            prompt_id="privacy-safe-id", model_invoked=False, tool_invoked=False,
        )
        return self.reviews.create_review(
            prompt_id="privacy-safe-id", audit_event_id=event_id, stage="INPUT",
            risk_category="H", risk_level="MEDIUM", score=0.55,
        )

    def test_policy_registry_has_explicit_version_and_provenance(self):
        policy = get_active_policy()
        self.assertEqual(policy.policy_version, "PIRAI-POLICY-1.0.0")
        self.assertTrue(policy.safety_classifier)
        self.assertTrue(policy.coding_model)
        self.assertTrue(policy.tool_policy_version)

    def test_audit_ids_are_unique_and_policy_bound(self):
        values = dict(stage="INPUT", decision="ALLOW", prompt_id="p", model_invoked=False, tool_invoked=False)
        first, second = self.audit(**values), self.audit(**values)
        self.assertNotEqual(first, second)
        events = [json.loads(line) for line in self.audit_path.read_text().splitlines()]
        self.assertTrue(all(item["event_id"].startswith("EVT-") for item in events))
        self.assertTrue(all(item["policy_version"] == get_active_policy().policy_version for item in events))

    def test_review_pipeline_persists_pending_and_never_invokes_model_or_tool(self):
        model_calls, tool_calls = [], []
        result = safe_coding_agent(
            "A medium risk fixture", prompt_id="case-review", safety_fn=review_gate,
            generate_fn=lambda text: model_calls.append(text),
            tool_request={"name": "read_file", "action": "read", "arguments": {}},
            trusted_permissions={"files:read"}, tool_execute_fn=lambda request: tool_calls.append(request),
            audit_fn=lambda **event: "EVT-20261001-ABC123", review_manager=self.reviews,
        )
        self.assertEqual(result["status"], "HUMAN_REVIEW")
        self.assertEqual(result["governance_status"], "PENDING")
        self.assertRegex(result["review_id"], r"^REV-\d{8}-[A-F0-9]{6}$")
        self.assertEqual(model_calls, [])
        self.assertEqual(tool_calls, [])
        record = self.reviews.get_review(result["review_id"])
        self.assertEqual(record.status, "PENDING")
        self.assertNotIn("A medium risk fixture", self.reviews.path.read_text())

    def test_review_persistence_failure_is_fail_closed(self):
        class FailingReviewManager:
            def create_review(self, **_values):
                raise GovernancePersistenceError("storage unavailable")

        model_calls = []
        result = safe_coding_agent(
            "A medium risk fixture", safety_fn=review_gate,
            generate_fn=lambda text: model_calls.append(text),
            audit_fn=lambda **event: "EVT-20261001-ABC123",
            review_manager=FailingReviewManager(),
        )
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["governance_status"], "PERSISTENCE_FAILED")
        self.assertEqual(model_calls, [])

    def test_approval_rejection_validation_and_immutability(self):
        approved = self.create_review()
        resolved = self.reviews.resolve_review(
            approved.review_id, reviewer_id="security-reviewer-01",
            decision="APPROVED", justification="Verified false positive against policy.",
        )
        self.assertEqual(resolved.status, "APPROVED")
        with self.assertRaises(ReviewAlreadyResolvedError):
            self.reviews.resolve_review(approved.review_id, reviewer_id="reviewer-2", decision="REJECTED", justification="Changed")

        rejected = self.create_review()
        self.assertEqual(self.reviews.resolve_review(
            rejected.review_id, reviewer_id="security-reviewer-02", decision="REJECTED",
            justification="Risk remains material.",
        ).status, "REJECTED")
        for reviewer, justification in [("", "reason"), ("reviewer", "")]:
            pending = self.create_review()
            with self.assertRaises(ReviewValidationError):
                self.reviews.resolve_review(pending.review_id, reviewer_id=reviewer, decision="APPROVED", justification=justification)
        with self.assertRaises(ReviewNotFoundError):
            self.reviews.resolve_review("REV-20261001-FFFFFF", reviewer_id="reviewer", decision="APPROVED", justification="reason")

    def test_override_is_separate_and_preserves_original_event(self):
        review = self.create_review()
        before = self.audit_path.read_text()
        override = self.overrides.create_override(
            audit_event_id=review.audit_event_id, review_id=review.review_id,
            original_decision="REVIEW", final_decision="ALLOW",
            reviewer_id="security-reviewer-01", reason="Documented false positive.",
        )
        self.assertEqual(override.original_decision, "REVIEW")
        self.assertEqual(self.audit_path.read_text(), before)
        self.assertEqual(len(self.overrides.list_overrides()), 1)
        with self.assertRaises(OverrideValidationError):
            self.overrides.create_override(
                audit_event_id="EVT-20261001-000000", original_decision="BLOCK",
                final_decision="ALLOW", reviewer_id="reviewer", reason="reason",
            )

    def test_report_uses_actual_records_and_states_insufficient_data(self):
        self.audit(stage="INPUT", decision="ALLOW", category=None, prompt_id="one", model_invoked=False, tool_invoked=False)
        self.audit(stage="TOOL_POLICY", decision="BLOCK", category="TOOL_ABUSE", prompt_id="two", model_invoked=False, tool_invoked=False)
        report = build_governance_report(
            audit_path=self.audit_path, review_manager=self.reviews, override_manager=self.overrides,
        )
        self.assertEqual(report["summary"]["total_security_decisions"], 2)
        self.assertEqual(report["summary"]["decision_counts"]["ALLOW"], 1)
        self.assertEqual(report["summary"]["decision_counts"]["BLOCK"], 1)
        self.assertEqual(report["summary"]["decision_counts"]["REVIEW"], 0)
        self.assertEqual(report["summary"]["tool_authorization_denials"], 1)
        self.assertFalse(report["data_quality"]["review_metrics_available"])

    def test_explanation_exposes_governance_metadata_not_hidden_reasoning(self):
        explanation = build_explanation(decision="REVIEW", detected_by="POLICY", event_id="EVT-1", review_id="REV-1")
        self.assertEqual(explanation["policy_version"], get_active_policy().policy_version)
        self.assertTrue(explanation["review_required"])
        self.assertNotIn("chain_of_thought", explanation)
        self.assertNotIn("system_prompt", explanation)


if __name__ == "__main__":
    unittest.main()
