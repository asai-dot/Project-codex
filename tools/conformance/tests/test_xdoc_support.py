"""DD-XDOC-001 v0.8 受入試験11 + B15/B16 の negative fixtures。

GPT 必須 fixture: empty-support-basis（B15）/ foreign-assessment-ref（B16）/
failed-current-coverage（B16）/ wrong-facet coverage（B16）。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_coverage import (  # noqa: E402
    CoveragePolicy, CoverageAssessment, CoverageClaimScope, CoverageStore,
)
from xdoc_support import (  # noqa: E402
    UseAssessmentRevisionRec, ClusterPolicy, SupportEdge, EdgeEvalContext,
    support_edge_effective, non_empty_required, SupportValidationError,
)

COVPOLICY = CoveragePolicy("COV-1", "v1", "table", "char_offset", 0.7, 0.7)
CPOLICY = ClusterPolicy(
    "CL-1", "v1", minimum_support_score=0.5, calibration_id="cal", calibration_version="1",
    required_basis_types=["use_assessment_revision", "coverage_assessment"],
    allowed_support_targets=["litlink"], allowed_support_purposes=["litlink_candidate"],
)
LOW, HIGH = "mLow", "mHigh"


def _ca(member, facet="table", selector="complete"):
    return CoverageAssessment(
        alignment_observation_id="obs1", member_ref=member, side="a", facet=facet,
        coordinate_space="char_offset", asset_hash="ah", source_text_revision_id="r1",
        selector_state=selector, covered_ranges=[(0, 200)], unknown_ranges=[(900, 901)],
        ocr_quality_score=0.9, layout_quality_score=0.9, coverage_policy_id="COV-1",
        coverage_policy_version="v1", coverage_revision_seq=1,
    )


def _ctx(coverage_assessments, ua_revs, scope_member=LOW):
    store = CoverageStore(COVPOLICY)
    for ca in coverage_assessments:
        store.add_assessment(ca)
    required_scope = {}
    for ca in coverage_assessments:
        required_scope[ca.member_ref] = CoverageClaimScope(
            "uak1", ca.member_ref, "char_offset", [(0, 50)], ca.assessment_id)
    return EdgeEvalContext(CPOLICY, {r.assessment_revision_id: r for r in ua_revs}, store, required_scope)


def _edge(ua_ids, cov_ids, facet="table", obs="obs1"):
    return SupportEdge(
        cluster_facet=facet, canonical_member_low=LOW, canonical_member_high=HIGH,
        alignment_observation_id=obs, support_score=0.9, calibration_id="cal", calibration_version="1",
        support_basis_use_assessment_revision_ids=ua_ids,
        support_basis_coverage_assessment_ids=cov_ids,
    )


def _good_ua(obs="obs1"):
    return UseAssessmentRevisionRec("ua1", obs, "active", "litlink_candidate", "litlink", "eligible")


class TestEmptyBasis(unittest.TestCase):
    def test_11a_empty_support_basis_false(self):
        """B15 empty-support-basis: 両配列空 → non_empty_required false → effective false。"""
        edge = _edge([], [])
        ctx = _ctx([], [])
        self.assertFalse(non_empty_required(edge, CPOLICY))
        self.assertFalse(support_edge_effective(edge, ctx))


class TestForeignAndFacet(unittest.TestCase):
    def _valid_setup(self, ua_obs="obs1", cov_member=LOW, cov_facet="table", cov_selector="complete",
                     edge_facet="table", edge_obs="obs1"):
        ca = _ca(cov_member, facet=cov_facet, selector=cov_selector)
        ctx = _ctx([ca], [_good_ua(ua_obs)])
        edge = _edge(["ua1"], [ca.assessment_id], facet=edge_facet, obs=edge_obs)
        return edge, ctx

    def test_positive_effective_true(self):
        edge, ctx = self._valid_setup()
        self.assertTrue(support_edge_effective(edge, ctx))

    def test_11b_foreign_assessment_ref_false(self):
        """B16 foreign-ref: use_assessment が別 alignment → false。"""
        edge, ctx = self._valid_setup(ua_obs="OTHER_OBS")
        self.assertFalse(support_edge_effective(edge, ctx))

    def test_11c_failed_current_coverage_false(self):
        """B16 failed-current-coverage: coverage current だが selector failed → complete でない → false。"""
        edge, ctx = self._valid_setup(cov_selector="failed")
        self.assertFalse(support_edge_effective(edge, ctx))

    def test_11d_wrong_facet_coverage_false(self):
        """B16 wrong-facet: coverage facet ≠ cluster_facet → false。"""
        edge, ctx = self._valid_setup(cov_facet="structure", edge_facet="table")
        self.assertFalse(support_edge_effective(edge, ctx))

    def test_coverage_member_not_in_edge_false(self):
        """B16: coverage member が low/high のいずれでもない → false。"""
        edge, ctx = self._valid_setup(cov_member="UNRELATED")
        self.assertFalse(support_edge_effective(edge, ctx))

    def test_ineligible_ua_rejected(self):
        ca = _ca(LOW)
        bad = UseAssessmentRevisionRec("ua1", "obs1", "active", "litlink_candidate", "litlink", "ineligible")
        store = CoverageStore(COVPOLICY)
        store.add_assessment(ca)
        ctx = EdgeEvalContext(CPOLICY, {"ua1": bad}, store,
                              {LOW: CoverageClaimScope("uak1", LOW, "char_offset", [(0, 50)], ca.assessment_id)})
        self.assertFalse(support_edge_effective(_edge(["ua1"], [ca.assessment_id]), ctx))

    def test_superseded_ua_rejected(self):
        ca = _ca(LOW)
        sup = UseAssessmentRevisionRec("ua1", "obs1", "superseded", "litlink_candidate", "litlink", "eligible")
        store = CoverageStore(COVPOLICY)
        store.add_assessment(ca)
        ctx = EdgeEvalContext(CPOLICY, {"ua1": sup}, store,
                              {LOW: CoverageClaimScope("uak1", LOW, "char_offset", [(0, 50)], ca.assessment_id)})
        self.assertFalse(support_edge_effective(_edge(["ua1"], [ca.assessment_id]), ctx))


class TestEdgeGuards(unittest.TestCase):
    def test_self_pair_rejected(self):
        with self.assertRaises(SupportValidationError):
            SupportEdge("table", "m", "m", "obs1", 0.9, "cal", "1", [], [])

    def test_duplicate_basis_rejected(self):
        with self.assertRaises(SupportValidationError):
            SupportEdge("table", LOW, HIGH, "obs1", 0.9, "cal", "1", ["a", "a"], [])


if __name__ == "__main__":
    unittest.main()
