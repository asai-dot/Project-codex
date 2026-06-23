"""DD-XDOC-001 v0.9 §10 受入試験11（support coverage scope ref B21 / policy B22 / revision B23）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_coverage import CoveragePolicy, CoverageAssessment, CoverageClaimScope, CoverageStore  # noqa: E402
from xdoc_support_revision import (  # noqa: E402
    ClusterPolicyV09, UseAssessmentRevisionRec, SupportEdgeV09, CoverageScopeRef,
    SupportEdgeStore, EdgeEvalContextV09, support_edge_effective,
    support_basis_valid_ua, covers_all_required_members, SupportRevisionError,
)

LOW, HIGH = "mLow", "mHigh"
FACET = "table"
ALN = "obs1"
COVPOL = CoveragePolicy("COV-1", "v1", FACET, "char_offset", 0.7, 0.7)


def _ca(member, facet=FACET, selector="complete"):
    return CoverageAssessment(
        alignment_observation_id=ALN, member_ref=member, side="a", facet=facet,
        coordinate_space="char_offset", asset_hash="h", source_text_revision_id="r1",
        selector_state=selector, covered_ranges=[(0, 200)], unknown_ranges=[(900, 901)],
        ocr_quality_score=0.9, layout_quality_score=0.9, coverage_policy_id="COV-1",
        coverage_policy_version="v1", coverage_revision_seq=1,
    )


def _policy(**over):
    base = dict(
        policy_id="CL-1", policy_version="v1", minimum_support_score=0.5,
        calibration_id="cal", calibration_version="1",
        required_basis_types=["use_assessment_revision", "coverage_assessment"],
        allowed_support_targets=["litlink"], allowed_support_purposes=["litlink_candidate"],
    )
    base.update(over)
    return ClusterPolicyV09(**base)


def _ua(eligibility="eligible"):
    return UseAssessmentRevisionRec("ua1", ALN, "active", "litlink_candidate", "litlink", eligibility)


def _setup(members=(LOW, HIGH), cov_facets=None, ua_elig="eligible"):
    cov_facets = cov_facets or {LOW: FACET, HIGH: FACET}
    store = CoverageStore(COVPOL)
    scopes = {}
    refs = []
    for m in members:
        ca = store.add_assessment(_ca(m, facet=cov_facets[m]))
        scope = CoverageClaimScope("uak1", m, "char_offset", [(0, 50)], ca.assessment_id)
        store.add_scope(scope)
        scopes[scope.coverage_claim_scope_id] = scope
        refs.append(CoverageScopeRef(scope.coverage_claim_scope_id, m))
    estore = SupportEdgeStore()
    policy = _policy()
    edge = estore.add(SupportEdgeV09(
        cluster_facet=FACET, canonical_member_low=LOW, canonical_member_high=HIGH,
        alignment_observation_id=ALN, support_score=0.9, calibration_id="cal", calibration_version="1",
        policy_id="CL-1", policy_version="v1", revision_seq=1,
        support_basis_use_assessment_revision_ids=["ua1"], support_basis_coverage_scope_refs=refs,
    ))
    ctx = EdgeEvalContextV09(
        policy=policy, store=estore, ua_revisions={"ua1": _ua(ua_elig)}, coverage_store=store,
        scopes=scopes, use_assessment_alignment_id=ALN, alignment_facet=FACET,
        side_of_member={LOW: "a", HIGH: "a"},
    )
    return edge, ctx, estore


class TestPositive(unittest.TestCase):
    def test_full_valid_effective(self):
        edge, ctx, _ = _setup()
        self.assertTrue(support_edge_effective(edge, ctx))


class TestB22Policy(unittest.TestCase):
    def test_11a_empty_required_basis_types_rejected(self):
        with self.assertRaises(SupportRevisionError):
            _policy(required_basis_types=[])

    def test_11b_hold_support_rejected(self):
        """hold の use_assessment は allowed_support_eligibilities（既定 eligible）外 → false。"""
        edge, ctx, _ = _setup(ua_elig="hold")
        self.assertFalse(support_basis_valid_ua(edge, "ua1", ctx))
        self.assertFalse(support_edge_effective(edge, ctx))


class TestB21CoverageScope(unittest.TestCase):
    def test_11c_missing_member_scope_false(self):
        """edge が low/high 双方の complete scope を持たない → covers_all_required_members false。"""
        edge, ctx, _ = _setup(members=(LOW,))  # HIGH の scope ref 欠落
        self.assertFalse(covers_all_required_members(edge, ctx))
        self.assertFalse(support_edge_effective(edge, ctx))

    def test_11d_wrong_facet_scope_false(self):
        """coverage scope の assessment facet ≠ cluster_facet → support_basis_valid_scope false。"""
        edge, ctx, _ = _setup(cov_facets={LOW: FACET, HIGH: "structure"})
        self.assertFalse(support_edge_effective(edge, ctx))


class TestB23Revision(unittest.TestCase):
    def test_11e_revision_supersede(self):
        """basis 追加で新 revision → 旧 revision superseded・新 active（silent mutation なし）。"""
        edge1, ctx, estore = _setup()
        # 同一 key・別 basis で revision_seq=2 を append
        refs2 = list(edge1.support_basis_coverage_scope_refs)
        edge2 = estore.add(SupportEdgeV09(
            cluster_facet=FACET, canonical_member_low=LOW, canonical_member_high=HIGH,
            alignment_observation_id=ALN, support_score=0.95, calibration_id="cal", calibration_version="1",
            policy_id="CL-1", policy_version="v1", revision_seq=2,
            support_basis_use_assessment_revision_ids=["ua1"], support_basis_coverage_scope_refs=refs2,
            supersedes_revision_id=edge1.support_edge_revision_id,
        ))
        self.assertEqual(edge1.support_edge_key_id, edge2.support_edge_key_id)
        self.assertEqual(estore.support_status(edge1), "superseded")
        self.assertEqual(estore.support_status(edge2), "active")
        # active(edge2) のみ effective 評価対象
        self.assertFalse(support_edge_effective(edge1, ctx))  # superseded → false

    def test_revoked_status(self):
        estore = SupportEdgeStore()
        e = estore.add(SupportEdgeV09(
            cluster_facet=FACET, canonical_member_low=LOW, canonical_member_high=HIGH,
            alignment_observation_id=ALN, support_score=0.9, calibration_id="cal", calibration_version="1",
            policy_id="CL-1", policy_version="v1", revision_seq=1,
            support_basis_use_assessment_revision_ids=["ua1"], support_basis_coverage_scope_refs=[],
            revoked=True,
        ))
        self.assertEqual(estore.support_status(e), "revoked")

    def test_unique_key_revision(self):
        estore = SupportEdgeStore()
        kw = dict(cluster_facet=FACET, canonical_member_low=LOW, canonical_member_high=HIGH,
                  alignment_observation_id=ALN, support_score=0.9, calibration_id="cal",
                  calibration_version="1", policy_id="CL-1", policy_version="v1", revision_seq=1,
                  support_basis_use_assessment_revision_ids=["ua1"], support_basis_coverage_scope_refs=[])
        estore.add(SupportEdgeV09(**kw))
        with self.assertRaises(SupportRevisionError):
            estore.add(SupportEdgeV09(**kw))


if __name__ == "__main__":
    unittest.main()
