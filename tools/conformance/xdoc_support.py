"""xdoc_support — DD-XDOC-001 v0.8 §10（support_edge 証拠拘束）。

依存ゼロ・read-only 純関数。受入試験11（a:空配列→false / b:foreign-ref→false /
c:failed-current-coverage→false / d:wrong-facet→false）を機械証明する。

- non_empty_required (B15): cluster_policy.required_basis_types で conditional non-empty
- support_basis_valid (B16): 型別 FK 整合（同一 alignment・member∈low/high・facet一致・
  coverage は current かつ complete・use_assessment は active かつ allowed purpose/target）
- support_edge_effective: 上記 + score/calibration
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from . import xdoc_coverage as _cov
except ImportError:  # pragma: no cover
    import xdoc_coverage as _cov


class SupportValidationError(ValueError):
    pass


# ---- records（§10） ----------------------------------------------------------------
@dataclass
class UseAssessmentRevisionRec:
    assessment_revision_id: str
    alignment_observation_id: str
    assessment_status: str  # active | superseded | revoked
    evaluation_purpose: str
    target: str
    eligibility: str  # eligible | ineligible | hold


@dataclass
class ClusterPolicy:
    policy_id: str
    policy_version: str
    minimum_support_score: float
    calibration_id: str
    calibration_version: str
    required_basis_types: List[str]  # {use_assessment_revision, coverage_assessment} 部分集合（既定=両方）
    allowed_support_targets: List[str]
    allowed_support_purposes: List[str]


@dataclass
class SupportEdge:
    cluster_facet: str
    canonical_member_low: str
    canonical_member_high: str
    alignment_observation_id: str
    support_score: float
    calibration_id: str
    calibration_version: str
    support_basis_use_assessment_revision_ids: List[str]
    support_basis_coverage_assessment_ids: List[str]
    support_edge_id: str = field(init=False)

    def __post_init__(self):
        if self.canonical_member_low == self.canonical_member_high:
            raise SupportValidationError("canonical_member_low ≠ canonical_member_high 必須")
        # B15: unique items
        for arr, nm in (
            (self.support_basis_use_assessment_revision_ids, "use_assessment_revision_ids"),
            (self.support_basis_coverage_assessment_ids, "coverage_assessment_ids"),
        ):
            if len(arr) != len(set(arr)):
                raise SupportValidationError(f"support_basis_{nm} は unique items")
        try:
            from . import xdoc_canonical as _xc
        except ImportError:  # pragma: no cover
            import xdoc_canonical as _xc
        self.support_edge_id = _xc.sha256_hex(_xc.canonical_json({
            "cluster_facet": self.cluster_facet,
            "canonical_member_low": self.canonical_member_low,
            "canonical_member_high": self.canonical_member_high,
            "alignment_observation_id": self.alignment_observation_id,
        }))


@dataclass
class EdgeEvalContext:
    """edge 評価に必要な参照解決器。required_scope_for は (edge, member) → CoverageClaimScope。"""
    policy: ClusterPolicy
    ua_revisions: Dict[str, UseAssessmentRevisionRec]
    coverage_store: "_cov.CoverageStore"
    required_scope_for: Dict[str, "_cov.CoverageClaimScope"]  # member_ref → required scope（edge 文脈）


# ---- predicates（§10-1） -----------------------------------------------------------
def non_empty_required(edge: SupportEdge, policy: ClusterPolicy) -> bool:
    """B15: required_basis_types が要求する配列は minItems=1。空→false。"""
    if "use_assessment_revision" in policy.required_basis_types:
        if len(edge.support_basis_use_assessment_revision_ids) < 1:
            return False
    if "coverage_assessment" in policy.required_basis_types:
        if len(edge.support_basis_coverage_assessment_ids) < 1:
            return False
    return True


def _ua_valid(edge: SupportEdge, ref_id: str, ctx: EdgeEvalContext) -> bool:
    r = ctx.ua_revisions.get(ref_id)
    if r is None:
        return False
    return (
        r.assessment_status == "active"
        and r.alignment_observation_id == edge.alignment_observation_id  # B16: 同一 alignment
        and r.target in ctx.policy.allowed_support_targets
        and r.evaluation_purpose in ctx.policy.allowed_support_purposes
        and r.eligibility != "ineligible"
    )


def _coverage_valid(edge: SupportEdge, ref_id: str, ctx: EdgeEvalContext) -> bool:
    c = ctx.coverage_store.get(ref_id)
    if c is None:
        return False
    if not (
        ctx.coverage_store.coverage_status(c) == "current"
        and c.alignment_observation_id == edge.alignment_observation_id  # B16: 同一 alignment
        and c.member_ref in (edge.canonical_member_low, edge.canonical_member_high)  # B16: member∈low/high
        and c.facet == edge.cluster_facet  # B16: facet 一致（wrong-facet を弾く）
    ):
        return False
    # B16: current だけでなく complete
    scope = ctx.required_scope_for.get(c.member_ref)
    if scope is None:
        return False
    return ctx.coverage_store.coverage_complete_for_scope(scope)


def support_basis_valid(edge: SupportEdge, ref_id: str, basis_ref_type: str,
                        ctx: EdgeEvalContext) -> bool:
    if basis_ref_type == "use_assessment_revision":
        return _ua_valid(edge, ref_id, ctx)
    if basis_ref_type == "coverage_assessment":
        return _coverage_valid(edge, ref_id, ctx)
    raise SupportValidationError(f"unknown basis_ref_type: {basis_ref_type}")


def support_edge_effective(edge: SupportEdge, ctx: EdgeEvalContext) -> bool:
    p = ctx.policy
    if not (
        edge.support_score >= p.minimum_support_score
        and edge.calibration_id == p.calibration_id
        and edge.calibration_version == p.calibration_version
    ):
        return False
    if not non_empty_required(edge, p):  # B15: 空配列 → false（vacuous truth 阻止）
        return False
    # B16: 全 basis ref が FK 整合
    for rid in edge.support_basis_use_assessment_revision_ids:
        if not support_basis_valid(edge, rid, "use_assessment_revision", ctx):
            return False
    for rid in edge.support_basis_coverage_assessment_ids:
        if not support_basis_valid(edge, rid, "coverage_assessment", ctx):
            return False
    return True
