import ast
from pathlib import Path
import typing
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "contracts" / "mod_appeal.py").read_text(encoding="utf-8")


def load_contract_rules():
    tree = ast.parse(SOURCE)
    selected = []
    wanted_functions = {"_has_evidence_slot", "_audit_evidence", "_allocate_bond"}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if "MAX_EVIDENCE_PER_SIDE" in names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected.append(node)
    namespace = {"typing": typing}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(ROOT), "exec"), namespace)
    return namespace


RULES = load_contract_rules()
has_slot = RULES["_has_evidence_slot"]
audit_evidence = RULES["_audit_evidence"]
allocate_bond = RULES["_allocate_bond"]


class EvidenceAndSettlementBehaviorTests(unittest.TestCase):
    BOND = 1_000_000_000_000_000_000

    def test_mismatched_appellant_commitment_cannot_recover_bond(self):
        audit = audit_evidence(
            ["APPELLANT", "MODERATOR"],
            ["MISMATCH", "VERIFIED"],
            "VERIFIED",
        )
        self.assertEqual(audit["valid_indices"], [1])
        self.assertEqual(audit["appellant_faults"], 1)
        allocation = allocate_bond(
            "INSUFFICIENT_EVIDENCE",
            self.BOND,
            audit["appellant_faults"],
            audit["moderator_faults"],
        )
        self.assertEqual(allocation["appellant_credit"], 0)
        self.assertEqual(allocation["community_credit"], self.BOND)
        self.assertEqual(allocation["rule"], "APPELLANT_INVALID_EVIDENCE_FORFEITURE")

    def test_appellant_fetch_failure_is_attributed_not_global_poison(self):
        audit = audit_evidence(
            ["APPELLANT", "APPELLANT"],
            ["UNAVAILABLE", "VERIFIED"],
            "VERIFIED",
        )
        self.assertEqual(audit["valid_indices"], [1])
        allocation = allocate_bond(
            "INSUFFICIENT_EVIDENCE",
            self.BOND,
            audit["appellant_faults"],
            audit["moderator_faults"],
        )
        self.assertEqual(allocation["appellant_credit"], 0)
        self.assertEqual(allocation["community_credit"], self.BOND)

    def test_moderator_fetch_failure_refunds_appellant(self):
        audit = audit_evidence(
            ["APPELLANT", "MODERATOR"],
            ["VERIFIED", "UNAVAILABLE"],
            "VERIFIED",
        )
        self.assertEqual(audit["valid_indices"], [0])
        allocation = allocate_bond(
            "VIOLATION_CONFIRMED",
            self.BOND,
            audit["appellant_faults"],
            audit["moderator_faults"],
        )
        self.assertEqual(allocation["appellant_credit"], self.BOND)
        self.assertEqual(allocation["community_credit"], 0)
        self.assertEqual(allocation["rule"], "MODERATOR_INVALID_EVIDENCE_REFUND")

    def test_bad_disputed_content_is_a_moderator_fault(self):
        audit = audit_evidence([], [], "MISMATCH")
        self.assertEqual(audit["moderator_faults"], 1)
        allocation = allocate_bond(
            "INSUFFICIENT_EVIDENCE",
            self.BOND,
            audit["appellant_faults"],
            audit["moderator_faults"],
        )
        self.assertEqual(allocation["appellant_credit"], self.BOND)
        self.assertEqual(allocation["community_credit"], 0)

    def test_both_parties_fault_split_preserves_total_bond(self):
        audit = audit_evidence(
            ["APPELLANT", "MODERATOR"],
            ["MISMATCH", "UNAVAILABLE"],
            "VERIFIED",
        )
        allocation = allocate_bond(
            "INSUFFICIENT_EVIDENCE",
            self.BOND,
            audit["appellant_faults"],
            audit["moderator_faults"],
        )
        self.assertEqual(allocation["appellant_credit"], self.BOND // 2)
        self.assertEqual(allocation["community_credit"], self.BOND // 2)
        self.assertEqual(
            allocation["appellant_credit"] + allocation["community_credit"],
            self.BOND,
        )

    def test_one_side_cannot_crowd_out_the_other(self):
        self.assertFalse(has_slot(6, 0, "APPELLANT"))
        self.assertTrue(has_slot(6, 0, "MODERATOR"))
        self.assertTrue(has_slot(0, 6, "APPELLANT"))
        self.assertFalse(has_slot(0, 6, "MODERATOR"))
        self.assertTrue(has_slot(5, 5, "APPELLANT"))
        self.assertTrue(has_slot(5, 5, "MODERATOR"))

    def test_clean_insufficient_evidence_keeps_normal_refund_rule(self):
        allocation = allocate_bond("INSUFFICIENT_EVIDENCE", self.BOND, 0, 0)
        self.assertEqual(allocation["appellant_credit"], self.BOND)
        self.assertEqual(allocation["community_credit"], 0)
        self.assertEqual(allocation["rule"], "VERDICT_APPELLANT_CREDIT")

    def test_partial_verdict_split_preserves_odd_bond(self):
        odd_bond = self.BOND + 1
        allocation = allocate_bond("PARTIAL_VIOLATION", odd_bond, 0, 0)
        self.assertEqual(
            allocation["appellant_credit"] + allocation["community_credit"],
            odd_bond,
        )
        self.assertEqual(allocation["community_credit"], allocation["appellant_credit"] + 1)


if __name__ == "__main__":
    unittest.main()
