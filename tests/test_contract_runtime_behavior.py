import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "mod_appeal.py"


class FakeUserError(Exception):
    pass


class Decorator:
    def __call__(self, target):
        return target

    @property
    def payable(self):
        return self


class DynArray(list):
    @classmethod
    def __class_getitem__(cls, _item):
        return cls


class TreeMap(dict):
    @classmethod
    def __class_getitem__(cls, _item):
        return cls

    def get_or_insert_default(self, key):
        if key not in self:
            self[key] = DynArray()
        return self[key]


class U256(int):
    pass


class FakeContract:
    balance = U256(0)


def load_contract_module():
    fake = types.ModuleType("genlayer")
    fake.gl = types.SimpleNamespace(
        Contract=FakeContract,
        public=types.SimpleNamespace(write=Decorator(), view=Decorator()),
        evm=types.SimpleNamespace(contract_interface=Decorator()),
        vm=types.SimpleNamespace(UserError=FakeUserError, Result=object, Return=object),
        message=types.SimpleNamespace(sender_address="", value=U256(0)),
    )
    fake.TreeMap = TreeMap
    fake.DynArray = DynArray
    fake.u256 = U256
    fake.Address = str
    previous = sys.modules.get("genlayer")
    sys.modules["genlayer"] = fake
    try:
        spec = importlib.util.spec_from_file_location("mod_appeal_runtime", CONTRACT_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            del sys.modules["genlayer"]
        else:
            sys.modules["genlayer"] = previous
    module._fake_gl = fake.gl
    return module


CONTRACT = load_contract_module()


class ContractRuntimeBehaviorTests(unittest.TestCase):
    APPELLANT = "0x00000000000000000000000000000000000000a1"
    MODERATOR = "0x00000000000000000000000000000000000000b2"
    BOND = 1_000_000_000_000_000_000

    def setUp(self):
        self.contract = CONTRACT.ModAppeal()
        self.contract.cases = TreeMap()
        self.contract.communities = TreeMap()
        self.contract.evidence = TreeMap()
        self.contract.evidence_seen = TreeMap()
        self.contract.total_adjudicated = U256(0)
        self.contract.total_paid = U256(0)
        self.contract._now = lambda: 100
        self.contract._transfer = lambda _recipient, _amount: None
        self.case_id = "behavior-case"
        self.contract.communities["behavior-community"] = json.dumps({
            "community_id": "behavior-community",
            "owner": self.APPELLANT,
        })
        self.contract.cases[self.case_id] = json.dumps({
            "case_id": self.case_id,
            "community_id": "behavior-community",
            "subject": self.APPELLANT,
            "moderator": self.MODERATOR,
            "action_type": "SUSPENSION",
            "content_url": "https://evidence.example/content.txt",
            "content_sha256": "1" * 64,
            "moderator_reason": "Reported promotional content.",
            "policy_version": 1,
            "status": "APPEAL_OPEN",
            "appeal_deadline": 200,
            "appellant": self.APPELLANT,
            "appeal_bond": str(self.BOND),
            "appellant_credit": "0",
            "community_credit": "0",
            "appellant_evidence_count": 0,
            "moderator_evidence_count": 0,
            "appellant_invalid_evidence": 0,
            "moderator_invalid_evidence": 0,
            "settlement_rule": "",
            "appellant_claimed": False,
            "community_claimed": False,
            "verdict": "",
            "confidence": 0,
            "verdict_reason": "",
            "adjudicated_at": 0,
            "finalized_at": 0,
        }, sort_keys=True)
        self.contract.evidence.get_or_insert_default(self.case_id)

    def submit(self, side, index, url=None):
        CONTRACT._fake_gl.message.sender_address = (
            self.APPELLANT if side == "APPELLANT" else self.MODERATOR
        )
        method = (
            self.contract.submit_evidence
            if side == "APPELLANT"
            else self.contract.submit_counter_evidence
        )
        method(
            self.case_id,
            url or f"https://evidence.example/{side.lower()}-{index}.txt",
            f"{index + 2:064x}"[-64:],
            f"{side} evidence {index}",
        )

    def close_window(self):
        case = json.loads(self.contract.cases[self.case_id])
        case["appeal_deadline"] = 50
        self.contract.cases[self.case_id] = json.dumps(case, sort_keys=True)

    @staticmethod
    def insufficient_decision(_case, items, _content, _texts):
        return {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "confidence": 20,
            "appellant_evidence": sum(item["side"] == "APPELLANT" for item in items),
            "moderator_evidence": sum(item["side"] == "MODERATOR" for item in items),
            "reason": "Verified evidence did not support a categorical policy decision.",
        }

    def test_appellant_cannot_crowd_out_moderator_reserved_slots(self):
        for index in range(6):
            self.submit("APPELLANT", index)
        with self.assertRaisesRegex(FakeUserError, "reserved evidence capacity"):
            self.submit("APPELLANT", 6)
        for index in range(6):
            self.submit("MODERATOR", index)
        case = json.loads(self.contract.cases[self.case_id])
        self.assertEqual(case["appellant_evidence_count"], 6)
        self.assertEqual(case["moderator_evidence_count"], 6)
        self.assertEqual(len(self.contract.evidence[self.case_id]), 12)

    def test_malicious_appellant_hash_is_excluded_and_bond_forfeited(self):
        bad_url = "https://evidence.example/appellant-bad.txt"
        good_url = "https://evidence.example/moderator-good.txt"
        self.submit("APPELLANT", 0, bad_url)
        self.submit("MODERATOR", 0, good_url)
        self.close_window()
        statuses = {
            "https://evidence.example/content.txt": "VERIFIED",
            bad_url: "MISMATCH",
            good_url: "VERIFIED",
        }
        self.contract._verify_snapshot = lambda url, _sha: {
            "status": statuses[url],
            "sha256": "",
            "text": "verified text" if statuses[url] == "VERIFIED" else "",
        }
        reviewed_sides = []

        def review(case, items, content, texts):
            reviewed_sides.extend(item["side"] for item in items)
            return self.insufficient_decision(case, items, content, texts)

        self.contract._review_case = review
        self.contract.adjudicate(self.case_id)
        case = json.loads(self.contract.cases[self.case_id])
        self.assertEqual(reviewed_sides, ["MODERATOR"])
        self.assertEqual(case["appellant_invalid_evidence"], 1)
        self.assertEqual(case["appellant_credit"], "0")
        self.assertEqual(case["community_credit"], str(self.BOND))
        self.assertEqual(case["settlement_rule"], "APPELLANT_INVALID_EVIDENCE_FORFEITURE")

    def test_appellant_fetch_failure_cannot_force_refund(self):
        unavailable_url = "https://evidence.example/appellant-offline.txt"
        self.submit("APPELLANT", 0, unavailable_url)
        self.close_window()
        self.contract._verify_snapshot = lambda url, _sha: {
            "status": "VERIFIED" if url.endswith("content.txt") else "UNAVAILABLE",
            "sha256": "",
            "text": "content" if url.endswith("content.txt") else "",
        }
        self.contract._review_case = self.insufficient_decision
        self.contract.adjudicate(self.case_id)
        case = json.loads(self.contract.cases[self.case_id])
        self.assertEqual(case["evidence_hash_statuses"], '["UNAVAILABLE"]')
        self.assertEqual(case["appellant_credit"], "0")
        self.assertEqual(case["community_credit"], str(self.BOND))

    def test_moderator_fetch_failure_cannot_capture_appellant_bond(self):
        unavailable_url = "https://evidence.example/moderator-offline.txt"
        self.submit("MODERATOR", 0, unavailable_url)
        self.close_window()
        self.contract._verify_snapshot = lambda url, _sha: {
            "status": "VERIFIED" if url.endswith("content.txt") else "UNAVAILABLE",
            "sha256": "",
            "text": "content" if url.endswith("content.txt") else "",
        }
        self.contract._review_case = lambda *_args: {
            "verdict": "VIOLATION_CONFIRMED",
            "confidence": 90,
            "appellant_evidence": 0,
            "moderator_evidence": 0,
            "reason": "The content otherwise appears to violate the policy.",
        }
        self.contract.adjudicate(self.case_id)
        case = json.loads(self.contract.cases[self.case_id])
        self.assertEqual(case["moderator_invalid_evidence"], 1)
        self.assertEqual(case["appellant_credit"], str(self.BOND))
        self.assertEqual(case["community_credit"], "0")
        self.assertEqual(case["settlement_rule"], "MODERATOR_INVALID_EVIDENCE_REFUND")

    def test_dual_role_wallet_can_claim_community_forfeiture(self):
        case = json.loads(self.contract.cases[self.case_id])
        case["status"] = "FINALIZED"
        case["appellant_credit"] = "0"
        case["community_credit"] = str(self.BOND)
        self.contract.cases[self.case_id] = json.dumps(case, sort_keys=True)
        CONTRACT._fake_gl.message.sender_address = self.APPELLANT
        self.contract.claim_bond(self.case_id)
        updated = json.loads(self.contract.cases[self.case_id])
        self.assertFalse(updated["appellant_claimed"])
        self.assertTrue(updated["community_claimed"])
        self.assertEqual(self.contract.total_paid, self.BOND)


if __name__ == "__main__":
    unittest.main()
