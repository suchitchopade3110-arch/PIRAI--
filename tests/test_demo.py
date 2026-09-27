import unittest

from agent.qwen_agent import safe_coding_agent
from demo.baseline_agent import run_baseline
from demo.runner import demo_generator, demo_safety_gate, evaluate_demo_cases, load_demo_cases, run_protected


class DemoSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {case["id"]: case for case in load_demo_cases()}

    def test_baseline_attack_reaches_generation_boundary(self):
        case = self.cases["direct_prompt_injection"]
        result = run_baseline(case["prompt"], case["id"], case["category"])
        self.assertTrue(result["model_invoked"])
        self.assertEqual(result["decision"], "VULNERABLE")

    def test_same_attack_is_blocked_before_generation(self):
        result = run_protected(self.cases["direct_prompt_injection"])
        self.assertEqual(result["decision"], "BLOCK")
        self.assertFalse(result["model_invoked"])

    def test_safe_request_is_allowed(self):
        result = run_protected(self.cases["safe_request"])
        self.assertEqual(result["decision"], "ALLOW")
        self.assertTrue(result["model_invoked"])

    def test_security_checks_precede_generation(self):
        result = run_protected(self.cases["safe_request"])
        stages = [event["stage"] for event in result["trace"]]
        self.assertLess(stages.index("JAILBREAK_DETECTION"), stages.index("QWEN_GENERATION"))
        self.assertLess(stages.index("INPUT_MODERATION"), stages.index("QWEN_GENERATION"))
        self.assertLess(stages.index("SAFETY_POLICY"), stages.index("QWEN_GENERATION"))

    def test_blocked_request_never_calls_generator(self):
        calls = []

        def tracked_generator(prompt):
            calls.append(prompt)
            return demo_generator(prompt)

        result = safe_coding_agent(
            self.cases["direct_prompt_injection"]["prompt"],
            safety_fn=demo_safety_gate,
            generate_fn=tracked_generator,
            audit_fn=lambda **kwargs: None,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(calls, [])

    def test_medium_risk_uses_existing_review_policy(self):
        result = run_protected(self.cases["medium_risk_fixture"])
        self.assertEqual(result["decision"], "REVIEW")
        self.assertFalse(result["model_invoked"])

    def test_demo_summary_is_execution_derived(self):
        evaluation = evaluate_demo_cases()
        self.assertEqual(evaluation["metrics"]["total_test_cases"], len(self.cases) - 1)
        self.assertEqual(evaluation["metrics"]["false_positives"], 0)
        self.assertEqual(evaluation["metrics"]["false_negatives"], 0)


if __name__ == "__main__":
    unittest.main()
