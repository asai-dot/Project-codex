"""DD-XDOC-001 v0.8 受入試験6 + B14/B17 の negative fixtures。

GPT 必須 fixture: missing-member-scope（B14）/ v9-v10 revision ordering（B17）。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_coverage import (  # noqa: E402
    CoveragePolicy, CoverageAssessment, CoverageClaimScope, ClaimContext, CoverageStore,
    contains, intersects, union, CoverageValidationError,
)

POLICY = CoveragePolicy("COV-1", "v1", "table", "char_offset", 0.7, 0.7)


def _ca(member, seq, selector="complete", covered=None, unknown=None, space="char_offset"):
    return CoverageAssessment(
        alignment_observation_id="obs1", member_ref=member, side="a", facet="table",
        coordinate_space=space, asset_hash="ah", source_text_revision_id="r1",
        selector_state=selector, covered_ranges=covered or [(0, 100)], unknown_ranges=unknown or [(900, 901)],
        ocr_quality_score=0.9, layout_quality_score=0.9, coverage_policy_id="COV-1",
        coverage_policy_version="v1", coverage_revision_seq=seq,
    )


class TestIntervalAdapter(unittest.TestCase):
    def test_contains_and_empty_covered(self):
        self.assertTrue(contains([(0, 100)], [(10, 50)]))
        self.assertFalse(contains([], [(10, 50)]))  # covered=[] は非空 required 包含不可
        self.assertFalse(contains([(0, 30)], [(10, 50)]))
        self.assertTrue(contains([(0, 30), (30, 60)], [(10, 50)]))  # half-open 隣接結合

    def test_unknown_intersection(self):
        self.assertTrue(intersects([(40, 60)], [(50, 70)]))
        self.assertFalse(intersects([(0, 10)], [(50, 70)]))


class TestRequiredScopeCompleteness(unittest.TestCase):
    def _store_with(self, registered_members):
        st = CoverageStore(POLICY)
        for m in registered_members:
            ca = st.add_assessment(_ca(m, seq=1, covered=[(0, 200)], unknown=[(900, 901)]))
            st.add_scope(CoverageClaimScope("uak1", m, "char_offset", [(0, 50)], ca.assessment_id))
        return st

    def test_06_missing_member_scope_false(self):
        """B14 missing-member-scope: claim は m1,m2 だが m1 のみ登録 → required ⊄ actual → false。"""
        ctx = ClaimContext("uak1", "absence", "a", ["m1", "m2"], "char_offset")
        st = self._store_with(["m1"])  # m2 の scope 未登録
        self.assertFalse(st.coverage_complete_for_use_assessment(ctx))

    def test_06_all_members_registered_complete_true(self):
        ctx = ClaimContext("uak1", "absence", "a", ["m1", "m2"], "char_offset")
        st = self._store_with(["m1", "m2"])
        self.assertTrue(st.coverage_complete_for_use_assessment(ctx))

    def test_failed_current_coverage_false(self):
        """B16: selector_state=failed の current は complete でない。"""
        st = CoverageStore(POLICY)
        ca = st.add_assessment(_ca("m1", seq=1, selector="failed", covered=[(0, 200)]))
        st.add_scope(CoverageClaimScope("uak1", "m1", "char_offset", [(0, 50)], ca.assessment_id))
        ctx = ClaimContext("uak1", "absence", "a", ["m1"], "char_offset")
        self.assertFalse(st.coverage_complete_for_use_assessment(ctx))


class TestRevisionOrdering(unittest.TestCase):
    def test_17_v9_v10_numeric_current(self):
        """B17: revision_seq=9,10 → current は 10（numeric）。string 'v9'>'v10' の誤りを回避。"""
        st = CoverageStore(POLICY)
        ca9 = st.add_assessment(_ca("m1", seq=9))
        ca10 = st.add_assessment(_ca("m1", seq=10))
        self.assertEqual(st.coverage_status(ca9), "superseded")
        self.assertEqual(st.coverage_status(ca10), "current")
        self.assertEqual(st.current_for_key(ca9.key_id).coverage_revision_seq, 10)

    def test_distinct_space_policy_no_supersede(self):
        """B17: 別 coordinate_space は別 key → 相互 supersede しない。"""
        st = CoverageStore(POLICY)
        ca_char = st.add_assessment(_ca("m1", seq=1, space="char_offset"))
        ca_page = st.add_assessment(_ca("m1", seq=1, space="page"))
        self.assertNotEqual(ca_char.key_id, ca_page.key_id)
        self.assertEqual(st.coverage_status(ca_char), "current")
        self.assertEqual(st.coverage_status(ca_page), "current")

    def test_unique_key_revision(self):
        st = CoverageStore(POLICY)
        st.add_assessment(_ca("m1", seq=1))
        with self.assertRaises(CoverageValidationError):
            st.add_assessment(_ca("m1", seq=1))  # UNIQUE(key, revision_seq)


class TestScopeNonEmpty(unittest.TestCase):
    def test_empty_required_ranges_rejected(self):
        with self.assertRaises(CoverageValidationError):
            CoverageClaimScope("uak1", "m1", "char_offset", [], "caid")


if __name__ == "__main__":
    unittest.main()
