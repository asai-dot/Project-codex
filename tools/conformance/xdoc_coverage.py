"""xdoc_coverage — DD-XDOC-001 v0.8 §9（coverage 完全性・logical key・numeric revision）。

依存ゼロ・read-only 純関数。受入試験6（必要scope完全性）と B17（v9/v10 → numeric revision で
決定的 current 選択）、B16 の coverage 側（current かつ complete）を機械証明する。

interval_1d adapter のみ実装（page/char_offset/token）。grid_2d/rect_2d は同契約で後続。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    from . import xdoc_canonical as _xc
    from . import xdoc_ranges as _rng
except ImportError:  # pragma: no cover
    import xdoc_canonical as _xc
    import xdoc_ranges as _rng

Range = Tuple  # interval_1d=(s,e) / grid_2d=(rs,re,cs,ce) / rect_2d=(p,x0,y0,x1,y1,sys)


class CoverageValidationError(ValueError):
    pass


# ---- interval_1d ヘルパ（後方互換・既存テスト用に再エクスポート） --------------------
_IV = _rng.get_adapter("char_offset")  # interval_1d adapter


def union(ranges):
    return _rng._iv_union(list(ranges)) if ranges else []


def contains(covered, required) -> bool:
    return _IV.contains(covered, required)


def intersects(a, b) -> bool:
    return _IV.intersects(a, b)


# ---- records（§9-2） ---------------------------------------------------------------
@dataclass
class CoveragePolicy:
    policy_id: str
    policy_version: str
    facet: str
    required_coordinate_space: str
    minimum_ocr_quality: float
    minimum_layout_quality: float


@dataclass
class CoverageAssessment:
    alignment_observation_id: str
    member_ref: str
    side: str
    facet: str
    coordinate_space: str
    asset_hash: str
    source_text_revision_id: str
    selector_state: str  # complete | partial | failed | not_applicable
    covered_ranges: List[Range]
    unknown_ranges: List[Range]
    ocr_quality_score: float
    layout_quality_score: float
    coverage_policy_id: str
    coverage_policy_version: str
    coverage_revision_seq: int  # B17: integer（string 順序非依存）
    key_id: str = field(init=False)
    payload_digest: str = field(init=False)
    assessment_id: str = field(init=False)

    def __post_init__(self):
        adapter = _rng.get_adapter(self.coordinate_space)
        adapter.check_nonempty(self.covered_ranges)
        adapter.check_nonempty(self.unknown_ranges)
        # B17: logical key に coordinate_space と policy_id を含む
        self.key_id = _xc.sha256_hex(_xc.canonical_json({
            "alignment_observation_id": self.alignment_observation_id,
            "member_ref": self.member_ref, "side": self.side, "facet": self.facet,
            "coordinate_space": self.coordinate_space, "coverage_policy_id": self.coverage_policy_id,
        }))
        self.payload_digest = _xc.sha256_hex(_xc.canonical_json({
            "asset_hash": self.asset_hash, "source_text_revision_id": self.source_text_revision_id,
            "selector_state": self.selector_state,
            "covered_ranges": [list(r) for r in self.covered_ranges],
            "unknown_ranges": [list(r) for r in self.unknown_ranges],
            "ocr_quality_score": self.ocr_quality_score, "layout_quality_score": self.layout_quality_score,
        }))
        self.assessment_id = _xc.sha256_hex(_xc.canonical_json({
            "coverage_assessment_key_id": self.key_id, "coverage_revision_seq": self.coverage_revision_seq,
            "coverage_policy_version": self.coverage_policy_version, "coverage_payload_digest": self.payload_digest,
        }))


@dataclass
class CoverageClaimScope:
    use_assessment_key_id: str
    member_ref: str
    required_coordinate_space: str
    required_ranges: List[Range]  # minItems=1
    coverage_assessment_id: str
    scope_key_id: str = field(init=False)            # B20 (v0.9 §9-3)
    coverage_claim_scope_id: str = field(init=False)

    def __post_init__(self):
        if not self.required_ranges:
            raise CoverageValidationError("required_ranges は minItems=1（空 scope 禁止・B14）")
        _rng.get_adapter(self.required_coordinate_space).check_nonempty(self.required_ranges)
        # B20: logical key = (use_assessment_key, member, coordinate_space) / scope id = (key, assessment)
        self.scope_key_id = _xc.sha256_hex(_xc.canonical_json({
            "use_assessment_key_id": self.use_assessment_key_id,
            "member_ref": self.member_ref,
            "required_coordinate_space": self.required_coordinate_space,
        }))
        self.coverage_claim_scope_id = _xc.sha256_hex(_xc.canonical_json({
            "scope_key_id": self.scope_key_id,
            "coverage_assessment_id": self.coverage_assessment_id,
        }))


@dataclass
class ClaimContext:
    use_assessment_key_id: str
    claim_kind: str  # presence | absence | difference | none
    claimed_side: str  # a | b | both
    claimed_member_refs: List[str]  # minItems=1
    required_coordinate_space: str

    @property
    def is_absence_or_difference(self) -> bool:
        return self.claim_kind in ("absence", "difference")


# ---- store + 完全性判定（§9-2/9-3） ------------------------------------------------
class CoverageStore:
    def __init__(self, policy: CoveragePolicy):
        self.policy = policy
        self._by_id: Dict[str, CoverageAssessment] = {}
        self._by_key: Dict[str, List[CoverageAssessment]] = {}
        self._scopes_by_uakey: Dict[str, List[CoverageClaimScope]] = {}

    def add_assessment(self, ca: CoverageAssessment) -> CoverageAssessment:
        if (ca.key_id, ca.coverage_revision_seq) in {
            (x.key_id, x.coverage_revision_seq) for x in self._by_key.get(ca.key_id, [])
        }:
            raise CoverageValidationError("UNIQUE(key, revision_seq) 違反")
        self._by_id[ca.assessment_id] = ca
        self._by_key.setdefault(ca.key_id, []).append(ca)
        return ca

    def add_scope(self, scope: CoverageClaimScope) -> None:
        self._scopes_by_uakey.setdefault(scope.use_assessment_key_id, []).append(scope)

    def get(self, assessment_id: str) -> Optional[CoverageAssessment]:
        return self._by_id.get(assessment_id)

    def coverage_status(self, ca: CoverageAssessment) -> str:
        """B17: current = max(revision_seq) over key（numeric）。"""
        peers = self._by_key.get(ca.key_id, [])
        max_seq = max(x.coverage_revision_seq for x in peers)
        return "current" if ca.coverage_revision_seq == max_seq else "superseded"

    def current_for_key(self, key_id: str) -> Optional[CoverageAssessment]:
        peers = self._by_key.get(key_id, [])
        return max(peers, key=lambda x: x.coverage_revision_seq) if peers else None

    def coverage_complete_for_scope(self, scope: CoverageClaimScope) -> bool:
        ca = self.get(scope.coverage_assessment_id)
        if ca is None:
            return False
        p = self.policy
        if ca.coordinate_space != scope.required_coordinate_space:
            return False
        adapter = _rng.get_adapter(ca.coordinate_space)  # range_class 別 set 演算
        return (
            self.coverage_status(ca) == "current"
            and ca.selector_state == "complete"
            and ca.ocr_quality_score >= p.minimum_ocr_quality
            and ca.layout_quality_score >= p.minimum_layout_quality
            and adapter.contains(ca.covered_ranges, scope.required_ranges)
            and not adapter.intersects(ca.unknown_ranges, scope.required_ranges)
        )

    # --- B14: 必要scope完全性 ---
    def required_scope_keys(self, ctx: ClaimContext) -> Set[Tuple[str, str]]:
        return {(m, ctx.required_coordinate_space) for m in ctx.claimed_member_refs}

    def actual_scope_keys(self, ua_key: str) -> Set[Tuple[str, str]]:
        return {
            (s.member_ref, s.required_coordinate_space)
            for s in self._scopes_by_uakey.get(ua_key, [])
        }

    def coverage_complete_for_use_assessment(self, ctx: ClaimContext) -> bool:
        ua_key = ctx.use_assessment_key_id
        # 必要 key が actual に全て含まれるか（未登録 member/scope → false）
        if not self.required_scope_keys(ctx) <= self.actual_scope_keys(ua_key):
            return False
        scopes = self._scopes_by_uakey.get(ua_key, [])
        if not scopes:
            return False
        return all(self.coverage_complete_for_scope(s) for s in scopes)

    # --- B20 (v0.9): coverage_claim_scope ↔ coverage_assessment の binding 整合 ---
    def coverage_scope_binding_valid(self, scope: "CoverageClaimScope",
                                     use_assessment_alignment_id: str,
                                     member_side: str, alignment_facet: str) -> bool:
        """scope が参照する coverage_assessment が同一 member/alignment/side/facet/policy か。

        member_side = alignment 内で scope.member_ref が属する side（呼び出し側が解決）。
        無関係 member の完全 coverage を差し替えられないことを保証する（B20）。
        """
        ca = self.get(scope.coverage_assessment_id)
        if ca is None:
            return False
        # 同一 scope key（key_id）に current assessment がちょうど1件
        peers = self._by_key.get(ca.key_id, [])
        currents = [x for x in peers if self.coverage_status(x) == "current"]
        if len(currents) != 1:
            return False
        return (
            scope.member_ref == ca.member_ref
            and ca.alignment_observation_id == use_assessment_alignment_id
            and ca.side == member_side
            and ca.facet == alignment_facet
            and ca.coverage_policy_id == self.policy.policy_id
            and ca.coverage_policy_version == self.policy.policy_version
        )
