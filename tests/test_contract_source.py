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
        self.assertIn("This party's reserved evidence capacity is full", SOURCE)
        self.assertIn("The referenced immutable policy version does not exist", SOURCE)
        self.assertIn("Policy fingerprint does not match the committed policy text", SOURCE)
        self.assertIn("invalid commitments are excluded and attributed", SOURCE)
        self.assertIn("def _verify_snapshot", SOURCE)
        self.assertIn("Retrieved disputed content:", SOURCE)
        self.assertIn('body[:MAX_SOURCE_CHARS].decode("utf-8")', SOURCE)
        self.assertNotIn("gl.nondet.web.render", SOURCE)

    def test_invalid_evidence_is_attributed_and_excluded(self):
        self.assertIn("def _audit_evidence", SOURCE)
        self.assertIn('verified_items.append(items[index])', SOURCE)
        self.assertIn('case["appellant_invalid_evidence"]', SOURCE)
        self.assertIn('case["moderator_invalid_evidence"]', SOURCE)
        self.assertNotIn("any(status != \"VERIFIED\" for status in evidence_statuses)", SOURCE)

    def test_fault_aware_bond_allocation_is_source_visible(self):
        self.assertIn("def _allocate_bond", SOURCE)
        self.assertIn("APPELLANT_INVALID_EVIDENCE_FORFEITURE", SOURCE)
        self.assertIn("MODERATOR_INVALID_EVIDENCE_REFUND", SOURCE)
        self.assertIn("BOTH_PARTIES_INVALID_EVIDENCE_SPLIT", SOURCE)

    def test_capacity_is_reserved_per_side(self):
        self.assertIn("MAX_EVIDENCE_PER_SIDE = 6", SOURCE)
        self.assertIn("def _has_evidence_slot", SOURCE)
        self.assertIn('case["appellant_evidence_count"]', SOURCE)
        self.assertIn('case["moderator_evidence_count"]', SOURCE)

    def test_settlement_is_separate_from_adjudication(self):
        self.assertIn('case["status"] = "ADJUDICATED"', SOURCE)
        self.assertIn('case["status"] = "FINALIZED"', SOURCE)
        self.assertIn("claim_bond", self.methods)
        self.assertIn("self.total_paid += amount", SOURCE)
        self.assertIn("is_appellant", SOURCE)
        self.assertIn("is_owner", SOURCE)


if __name__ == "__main__":
    unittest.main()
