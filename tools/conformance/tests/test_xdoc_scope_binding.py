"""DD-XDOC-001 v0.9 §9-3 受入試験6b（coverage_scope_binding_valid・無関係 coverage 差替え封じ）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_coverage import (  # noqa: E402
    CoveragePolicy, CoverageAssessment, CoverageClaimScope, CoverageStore,
)

POLICY = CoveragePolicy("COV-1", "v1", "table", "char_offset", 0.7, 0.7)


def _ca(member="m1", side="a", facet="table", aln="obs1", pol="COV-1", polver="v1", seq=1):
    return CoverageAssessment(
        alignment_observation_id=aln, member_ref=member, side=side, facet=facet,
        coordinate_space="char_offset", asset_hash="h", source_text_revision_id="r1",
        selector_state="complete", covered_ranges=[(0, 200)], unknown_ranges=[(900, 901)],
        ocr_quality_score=0.9, layout_quality_score=0.9, coverage_policy_id=pol,
        coverage_policy_version=polver, coverage_revision_seq=seq,
    )


def _store_scope(ca):
    st = CoverageStore(POLICY)
    st.add_assessment(ca)
    scope = CoverageClaimScope("uak1", ca.member_ref, "char_offset", [(0, 50)], ca.assessment_id)
    st.add_scope(scope)
    return st, scope


class TestScopeBinding(unittest.TestCase):
    def test_valid_binding(self):
        st, scope = _store_scope(_ca(member="m1", side="a", facet="table", aln="obs1"))
        self.assertTrue(st.coverage_scope_binding_valid(scope, "obs1", "a", "table"))

    def test_6b_wrong_member(self):
        """scope.member_ref ≠ ca.member_ref → false。"""
        st = CoverageStore(POLICY)
        ca = _ca(member="OTHER")
        st.add_assessment(ca)
        scope = CoverageClaimScope("uak1", "m1", "char_offset", [(0, 50)], ca.assessment_id)
        st.add_scope(scope)
        self.assertFalse(st.coverage_scope_binding_valid(scope, "obs1", "a", "table"))

    def test_6b_wrong_alignment(self):
        st, scope = _store_scope(_ca(aln="obs1"))
        self.assertFalse(st.coverage_scope_binding_valid(scope, "DIFFERENT_OBS", "a", "table"))

    def test_6b_wrong_side(self):
        st, scope = _store_scope(_ca(side="a"))
        self.assertFalse(st.coverage_scope_binding_valid(scope, "obs1", "b", "table"))

    def test_6b_wrong_facet(self):
        st, scope = _store_scope(_ca(facet="table"))
        self.assertFalse(st.coverage_scope_binding_valid(scope, "obs1", "a", "structure"))

    def test_6b_wrong_policy_version(self):
        st, scope = _store_scope(_ca(polver="v2"))
        self.assertFalse(st.coverage_scope_binding_valid(scope, "obs1", "a", "table"))


if __name__ == "__main__":
    unittest.main()
