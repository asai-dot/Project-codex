"""DD-XDOC-001 v0.9 §6 受入試験6a（claim member selector・過少申告封じ）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_claim import (  # noqa: E402
    ClaimMemberSelector, claim_member_complete, subset_selector_id,
    expected_member_set, ClaimValidationError,
    MODE_ALL_ON_SIDE, MODE_EXPLICIT_SUBSET,
)

A = ["a1", "a2"]
B = ["b1"]


class TestExpectedSet(unittest.TestCase):
    def test_sides(self):
        self.assertEqual(expected_member_set(A, B, "a"), {"a1", "a2"})
        self.assertEqual(expected_member_set(A, B, "b"), {"b1"})
        self.assertEqual(expected_member_set(A, B, "both"), {"a1", "a2", "b1"})


class TestAllOnSide(unittest.TestCase):
    def test_6a_both_one_member_rejected(self):
        """claimed_side=both で1 member だけ列挙 → all_on_side で不一致 → false。"""
        sel = ClaimMemberSelector("uak1", MODE_ALL_ON_SIDE, "both", ["a1"])
        self.assertFalse(claim_member_complete(sel, A, B))

    def test_all_members_complete(self):
        sel = ClaimMemberSelector("uak1", MODE_ALL_ON_SIDE, "both", ["a1", "a2", "b1"])
        self.assertTrue(claim_member_complete(sel, A, B))

    def test_side_a_complete(self):
        sel = ClaimMemberSelector("uak1", MODE_ALL_ON_SIDE, "a", ["a1", "a2"])
        self.assertTrue(claim_member_complete(sel, A, B))


class TestExplicitSubset(unittest.TestCase):
    def test_subset_requires_hash(self):
        sel = ClaimMemberSelector("uak1", MODE_EXPLICIT_SUBSET, "both", ["a1"])  # hash 未設定
        self.assertFalse(claim_member_complete(sel, A, B))

    def test_subset_with_correct_hash(self):
        sid = subset_selector_id(["a1"], "both")
        sel = ClaimMemberSelector("uak1", MODE_EXPLICIT_SUBSET, "both", ["a1"], subset_selector_id_value=sid)
        self.assertTrue(claim_member_complete(sel, A, B))  # subset は記録として残る

    def test_subset_wrong_hash_rejected(self):
        sel = ClaimMemberSelector("uak1", MODE_EXPLICIT_SUBSET, "both", ["a1"], subset_selector_id_value="deadbeef")
        self.assertFalse(claim_member_complete(sel, A, B))

    def test_subset_not_in_expected_rejected(self):
        sid = subset_selector_id(["zzz"], "both")
        sel = ClaimMemberSelector("uak1", MODE_EXPLICIT_SUBSET, "both", ["zzz"], subset_selector_id_value=sid)
        self.assertFalse(claim_member_complete(sel, A, B))  # claimed ⊄ expected


class TestGuards(unittest.TestCase):
    def test_empty_claimed_rejected(self):
        with self.assertRaises(ClaimValidationError):
            ClaimMemberSelector("uak1", MODE_ALL_ON_SIDE, "both", [])

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ClaimValidationError):
            ClaimMemberSelector("uak1", "bogus", "both", ["a1"])


if __name__ == "__main__":
    unittest.main()
