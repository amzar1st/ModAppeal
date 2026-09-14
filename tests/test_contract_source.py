import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "contracts" / "mod_appeal.py").read_text(encoding="utf-8")


class ContractSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(SOURCE)
        cls.contract = next(
            node for node in cls.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "ModAppeal"
        )
        cls.methods = {node.name: node for node in cls.contract.body if isinstance(node, ast.FunctionDef)}

    def test_public_workflow_methods_exist(self):
        expected = {
            "create_community", "publish_policy", "register_moderator", "record_action",
            "open_appeal", "submit_evidence", "submit_counter_evidence", "adjudicate",
            "finalize", "claim_bond", "get_case", "get_result", "get_case_evidence",
        }
        self.assertTrue(expected.issubset(self.methods))

    def test_consensus_and_four_outcomes_are_source_visible(self):
        self.assertIn("gl.vm.run_nondet_unsafe", SOURCE)
        for outcome in (
            "VIOLATION_CONFIRMED", "ACTION_OVERTURNED",
            "PARTIAL_VIOLATION", "INSUFFICIENT_EVIDENCE",
        ):
            self.assertIn(outcome, SOURCE)

    def test_policy_version_and_evidence_commitments_are_enforced(self):
        self.assertIn("Policy versions must increase exactly by one", SOURCE)
        self.assertIn("Policy fingerprint must be a 64-character SHA-256 hash", SOURCE)
        self.assertIn("Evidence fingerprint must be a 64-character SHA-256 hash", SOURCE)
        self.assertIn("This evidence URL was already submitted", SOURCE)
        self.assertIn("The referenced immutable policy version does not exist", SOURCE)
        self.assertIn("Policy fingerprint does not match the committed policy text", SOURCE)
        self.assertIn("The committed content or evidence bytes could not be verified", SOURCE)
        self.assertIn("def _verify_snapshot", SOURCE)

    def test_settlement_is_separate_from_adjudication(self):
        self.assertIn('case["status"] = "ADJUDICATED"', SOURCE)
        self.assertIn('case["status"] = "FINALIZED"', SOURCE)
        self.assertIn("claim_bond", self.methods)
        self.assertIn("self.total_paid += amount", SOURCE)


if __name__ == "__main__":
    unittest.main()
