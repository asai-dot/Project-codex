"""xdoc_support_revision — DD-XDOC-001 v0.9 §10（support edge の coverage scope ref / policy / revision）。

依存ゼロ・read-only 純関数。v0.8 の xdoc_support.py（B15/B16）を壊さず、v0.9 で追加された
B21（coverage scope ref + covers_all_required_members）・B22（policy non-empty + eligibility）・
B23（support edge revision append-only）を実装する。受入試験11(a-e) を機械証明。

参照: docs/dd_candidates/DD-XDOC-001_..._v0.9_20260623.md §10
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from . import xdoc_canonical as _xc
    from . import xdoc_coverage as _cov
except ImportError:  # pragma: no cover
    import xdoc_canonical as _xc
    import xdoc_coverage as _cov


class SupportRevisionError(ValueError):
    pass


# ---- records（§10-1/10-3） ---------------------------------------------------------
@dataclass
class UseAssessmentRevisionRec:
    assessment_revision_id: str
    alignment_observation_id: str
    assessment_status: str  # active | superseded | revoked
    evaluation_purpose: str
    target: str
    eligibility: str  # eligible | ineligible | hold


@dataclass
class ClusterPolicyV09:
    policy_id: str
    policy_version: str
    minimum_support_score: float
    calibration_id: str
    calibration_version: str
    required_basis_types: List[str]            # B22: minItems=1・unique
    allowed_support_targets: List[str]
    allowed_support_purposes: List[str]
    allowed_support_eligibilities: List[str] = field(default_factory=lambda: ["eligible"])  # B22 既定

    def __post_init__(self):
        # B22: required_basis_types / allowed_support_eligibilities は空不可・unique
        if not self.required_basis_types:
            raise SupportRevisionError("required_basis_types は minItems=1（空 policy 禁止・B22）")
        if len(self.required_basis_types) != len(set(self.required_basis_types)):
            raise SupportRevisionError("required_basis_types は unique")
        if not self.allowed_support_eligibilities:
            raise SupportRevisionError("allowed_support_eligibilities は minItems=1（B22）")


@dataclass(frozen=True)
class CoverageScopeRef:
    coverage_claim_scope_id: str
    member_ref: str  # low/high のいずれか


@dataclass
class SupportEdgeV09:
    cluster_facet: str
    canonical_member_low: str
    canonical_member_high: str
    alignment_observation_id: str
    support_score: float
    calibration_id: str
    calibration_version: str
    policy_id: str
    policy_version: str
    revision_seq: int
    support_basis_use_assessment_revision_ids: List[str]
    support_basis_coverage_scope_refs: List[CoverageScopeRef]
    revoked: bool = False
    supersedes_revision_id: Optional[str] = None
    support_edge_key_id: str = field(init=False)
    basis_digest: str = field(init=False)
    support_edge_revision_id: str = field(init=False)

    def __post_init__(self):
        if self.canonical_member_low == self.canonical_member_high:
            raise SupportRevisionError("low ≠ high 必須")
        ua = self.support_basis_use_assessment_revision_ids
        sc = [r.coverage_claim_scope_id for r in self.support_basis_coverage_scope_refs]
        if len(ua) != len(set(ua)) or len(sc) != len(set(sc)):
            raise SupportRevisionError("support_basis は unique items")
        self.support_edge_key_id = _xc.sha256_hex(_xc.canonical_json({
            "cluster_facet": self.cluster_facet,
            "canonical_member_low": self.canonical_member_low,
            "canonical_member_high": self.canonical_member_high,
            "alignment_observation_id": self.alignment_observation_id,
        }))
        # B23: basis_digest = sorted ua ids + sorted coverage scope ids
        self.basis_digest = _xc.sha256_hex(_xc.canonical_json({
            "ua": sorted(ua), "scopes": sorted(sc),
        }))
        self.support_edge_revision_id = _xc.sha256_hex(_xc.canonical_json({
            "key": self.support_edge_key_id, "basis_digest": self.basis_digest,
            "calibration_id": self.calibration_id, "calibration_version": self.calibration_version,
            "policy_id": self.policy_id, "policy_version": self.policy_version,
            "revision_seq": self.revision_seq,
        }))


# ---- store（B23: revision/status 導出） --------------------------------------------
class SupportEdgeStore:
    def __init__(self):
        self._by_key: Dict[str, List[SupportEdgeV09]] = {}

    def add(self, e: SupportEdgeV09) -> SupportEdgeV09:
        peers = self._by_key.setdefault(e.support_edge_key_id, [])
        if any(p.revision_seq == e.revision_seq for p in peers):
            raise SupportRevisionError("UNIQUE(key, revision_seq) 違反")
        peers.append(e)
        return e

    def support_status(self, e: SupportEdgeV09) -> str:
        """B23: revoked→revoked / max seq 非revoked→active / else superseded。"""
        if e.revoked:
            return "revoked"
        peers = self._by_key.get(e.support_edge_key_id, [])
        max_seq = max(p.revision_seq for p in peers)
        return "active" if e.revision_seq == max_seq else "superseded"


# ---- 評価 context ------------------------------------------------------------------
@dataclass
class EdgeEvalContextV09:
    policy: ClusterPolicyV09
    store: SupportEdgeStore
    ua_revisions: Dict[str, UseAssessmentRevisionRec]
    coverage_store: "_cov.CoverageStore"
    scopes: Dict[str, "_cov.CoverageClaimScope"]
    use_assessment_alignment_id: str
    alignment_facet: str
    side_of_member: Dict[str, str]


# ---- predicates（§10-2） -----------------------------------------------------------
def non_empty_required(edge: SupportEdgeV09, policy: ClusterPolicyV09) -> bool:
    if "use_assessment_revision" in policy.required_basis_types:
        if len(edge.support_basis_use_assessment_revision_ids) < 1:
            return False
    if "coverage_assessment" in policy.required_basis_types:
        if len(edge.support_basis_coverage_scope_refs) < 1:
            return False
    return True


def support_basis_valid_ua(edge: SupportEdgeV09, ref_id: str, ctx: EdgeEvalContextV09) -> bool:
    r = ctx.ua_revisions.get(ref_id)
    if r is None:
        return False
    return (
        r.assessment_status == "active"
        and r.alignment_observation_id == edge.alignment_observation_id
        and r.target in ctx.policy.allowed_support_targets
        and r.evaluation_purpose in ctx.policy.allowed_support_purposes
        and r.eligibility in ctx.policy.allowed_support_eligibilities  # B22: hold は既定 eligible 外
    )


def support_basis_valid_scope(edge: SupportEdgeV09, sref: CoverageScopeRef,
                              ctx: EdgeEvalContextV09) -> bool:
    if sref.member_ref not in (edge.canonical_member_low, edge.canonical_member_high):
        return False
    scope = ctx.scopes.get(sref.coverage_claim_scope_id)
    if scope is None or scope.member_ref != sref.member_ref:
        return False
    ca = ctx.coverage_store.get(scope.coverage_assessment_id)
    if ca is None or ca.facet != edge.cluster_facet:
        return False
    member_side = ctx.side_of_member.get(sref.member_ref)
    if member_side is None:
        return False
    # §9-3 binding + complete
    if not ctx.coverage_store.coverage_scope_binding_valid(
        scope, ctx.use_assessment_alignment_id, member_side, ctx.alignment_facet
    ):
        return False
    return ctx.coverage_store.coverage_complete_for_scope(scope)


def covers_all_required_members(edge: SupportEdgeV09, ctx: EdgeEvalContextV09) -> bool:
    """B21: coverage_assessment 必須 policy なら low/high 双方に valid scope。"""
    if "coverage_assessment" not in ctx.policy.required_basis_types:
        return True
    valid_members = {
        sref.member_ref for sref in edge.support_basis_coverage_scope_refs
        if support_basis_valid_scope(edge, sref, ctx)
    }
    return {edge.canonical_member_low, edge.canonical_member_high} <= valid_members


def support_edge_effective(edge: SupportEdgeV09, ctx: EdgeEvalContextV09) -> bool:
    p = ctx.policy
    if ctx.store.support_status(edge) != "active":   # B23: active revision のみ
        return False
    if not (edge.support_score >= p.minimum_support_score
            and edge.calibration_id == p.calibration_id
            and edge.calibration_version == p.calibration_version):
        return False
    if not non_empty_required(edge, p):              # B22
        return False
    for rid in edge.support_basis_use_assessment_revision_ids:
        if not support_basis_valid_ua(edge, rid, ctx):
            return False
    if not covers_all_required_members(edge, ctx):   # B21
        return False
    for sref in edge.support_basis_coverage_scope_refs:
        if not support_basis_valid_scope(edge, sref, ctx):
            return False
    return True
