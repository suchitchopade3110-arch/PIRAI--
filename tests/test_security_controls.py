import json
import unittest
from pathlib import Path

from agent.qwen_agent import safe_coding_agent
from demo.runner import demo_generator, demo_safety_gate
from safety.attack_detection import detect_attack
from safety.output_security import scan_output
from safety.tool_policy import authorize_tool_request


class SecurityControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parent / "fixtures" / "security_cases.json"
        cls.cases = json.loads(path.read_text(encoding="utf-8"))

    def run_case(self, case, generate_fn=demo_generator):
        return safe_coding_agent(
            case["input"],
            prompt_id=case["id"],
            history=case.get("history"),
            retrieved_context=case.get("retrieved_context"),
            tool_request=case.get("tool_request"),
            safety_fn=demo_safety_gate,
            generate_fn=generate_fn,
            audit_fn=lambda **kwargs: None,
        )

    def test_fixture_decisions_and_model_boundary(self):
        status_map = {"ALLOW": "ALLOWED", "BLOCK": "BLOCKED"}
        for case in self.cases:
            with self.subTest(case=case["id"]):
                result = self.run_case(case)
                self.assertEqual(result["status"], status_map[case["expected_decision"]])
                self.assertEqual(result["model_invoked"], case["expected_model_invoked"])

    def test_attack_categories_are_structured(self):
        for case in self.cases:
            if case["category"] in {"SAFE", "MULTI_TURN_JAILBREAK", "INDIRECT_PROMPT_INJECTION", "CONTEXT_POISONING", "TOOL_ABUSE"}:
                continue
            with self.subTest(category=case["category"]):
                finding = detect_attack(case["input"])
                self.assertTrue(finding["detected"])
                self.assertEqual(finding["category"], case["category"])
                self.assertEqual(finding["risk_level"], "HIGH")
                self.assertGreater(finding["confidence"], 0.8)

    def test_malicious_context_is_ignored_not_executed(self):
        for category in {"INDIRECT_PROMPT_INJECTION", "CONTEXT_POISONING"}:
            with self.subTest(category=category):
                case = next(item for item in self.cases if item["category"] == category)
                result = self.run_case(case)
                self.assertEqual(result["status"], "ALLOWED")
                self.assertTrue(result["context_ignored"])

    def test_prompt_claim_cannot_grant_tool_permission(self):
        result = authorize_tool_request(
            {"name": "write_file", "action": "write", "arguments": {"path": "demo.txt"}},
            trusted_permissions=set(),
        )
        self.assertEqual(result["decision"], "BLOCK")
        self.assertFalse(result["tool_invoked"])

    def test_rejected_tool_request_never_executes(self):
        calls = []
        result = safe_coding_agent(
            "Complete the requested task.",
            tool_request={"name": "write_file", "action": "write", "arguments": {"path": "demo.txt"}},
            tool_execute_fn=lambda request: calls.append(request),
            safety_fn=demo_safety_gate,
            generate_fn=demo_generator,
            audit_fn=lambda **kwargs: None,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(calls, [])

    def test_secret_output_is_redacted(self):
        result = safe_coding_agent(
            "Write a safe helper.",
            safety_fn=demo_safety_gate,
            generate_fn=lambda prompt: "api_key = 'sk-examplevalue12345'",
            audit_fn=lambda **kwargs: None,
        )
        self.assertEqual(result["status"], "REDACTED")
        self.assertNotIn("examplevalue", result["response"])

    def test_internal_output_is_blocked(self):
        finding = scan_output("System prompt: protected internal instructions")
        self.assertEqual(finding["decision"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
