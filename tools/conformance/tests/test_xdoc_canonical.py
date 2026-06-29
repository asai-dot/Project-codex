"""DD-XDOC-001 v0.7 受入試験のうち ID canonicalization 系（9, 10, 13/self-loop）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_canonical import (  # noqa: E402
    Alignment, MemberTuple, XdocValidationError,
    CARD_ONE_ONE, CARD_ONE_N, CARD_N_ONE, CARD_N_M,
    determine_cardinality,
)


def _align(direction, a, b, **over):
    base = dict(
        schema_version="xdoc-0.7", facet="text", comparison_intent="text_reuse",
        direction=direction, members_a=a, members_b=b,
        primary_method_registry_id="MR_minhash_v1",
        applied_companion_method_registry_ids=[],
        parameter_profile_hash="ph0", normalization_profile_id="np", normalization_profile_version="1",
        tokenization_profile_id="tp", tokenization_profile_version="1",
        corpus_snapshot_id="snap1", release_id="rel1",
    )
    base.update(over)
    return Alignment(**base)


M = MemberTuple
A1 = [M("assetA", "r1", "u1")]
B1 = [M("assetB", "r1", "u9")]
BN = [M("assetB", "r1", "u9"), M("assetB", "r1", "u10")]  # 複数 member side


class TestSymmetricId(unittest.TestCase):
    def test_09_symmetric_side_swap_same_id(self):
        """受入試験9: symmetric は side 入替で同一 observation_id。"""
        id_ab = _align("symmetric", A1, B1).observation_id()
        id_ba = _align("symmetric", B1, A1).observation_id()
        self.assertEqual(id_ab, id_ba)

    def test_09_symmetric_multimember_side_first_unique(self):
        """受入試験9: multi-member side が辞書順先頭でも cardinality 一意（n_m / one_n）。"""
        # assetB の u9/u10 は assetA u1 より辞書順で後でも先でも、unordered で one_n に正規化
        a_swapped = _align("symmetric", BN, A1)
        b_swapped = _align("symmetric", A1, BN)
        self.assertEqual(a_swapped.cardinality, CARD_ONE_N)
        self.assertEqual(b_swapped.cardinality, CARD_ONE_N)
        self.assertEqual(a_swapped.observation_id(), b_swapped.observation_id())

    def test_symmetric_never_n_one(self):
        self.assertEqual(determine_cardinality("symmetric", BN, A1), CARD_ONE_N)
        self.assertEqual(determine_cardinality("symmetric", A1, A1), CARD_ONE_ONE)

    def test_directional_keeps_order_and_n_one(self):
        """directional は入替で別 id・n_one を保持。"""
        ab = _align("a_to_b", BN, A1)
        self.assertEqual(ab.cardinality, CARD_N_ONE)
        ba = _align("a_to_b", A1, BN)
        self.assertEqual(ba.cardinality, CARD_ONE_N)
        self.assertNotEqual(ab.observation_id(), ba.observation_id())


class TestCompanionAndDrift(unittest.TestCase):
    def test_10_companion_set_changes_id(self):
        """受入試験10: applied companion set の変化で observation_id 変化。"""
        base = _align("symmetric", A1, B1).observation_id()
        with_hash = _align(
            "symmetric", A1, B1,
            applied_companion_method_registry_ids=["MR_content_hash_v1"],
        ).observation_id()
        self.assertNotEqual(base, with_hash)

    def test_10_field_drift_changes_id(self):
        base = _align("symmetric", A1, B1).observation_id()
        for over in (
            {"comparison_intent": "near_duplicate"},
            {"facet": "structure"},
            {"corpus_snapshot_id": "snap2"},
            {"parameter_profile_hash": "ph1"},
            {"normalization_profile_version": "2"},
        ):
            self.assertNotEqual(base, _align("symmetric", A1, B1, **over).observation_id(), over)


class TestSelfLoopGuards(unittest.TestCase):
    def test_self_overlap_rejected(self):
        with self.assertRaises(XdocValidationError):
            _align("symmetric", A1, A1)  # 両 side に同一 member

    def test_intra_side_dup_rejected(self):
        with self.assertRaises(XdocValidationError):
            _align("symmetric", [M("a", "r", "u"), M("a", "r", "u")], B1)

    def test_empty_side_rejected(self):
        with self.assertRaises(XdocValidationError):
            _align("symmetric", [], B1)


if __name__ == "__main__":
    unittest.main()
