"""xmodal_agreement — DD-XMODAL-001 v0.4 の confirmed/possible 判定（反こたつ記事の核）。

依存ゼロ・read-only 純関数。3軸（V=視覚/T=テキスト/D=外部法体系）の合意を、独立性を壊さずに
判定する。要点（DD-XMODAL v0.3/v0.4）:
- D0(prior)/D1(mapper, T結合=非独立)/D2(外部証拠) のうち **confirmed に効くのは D2 のみ**。
- confirmed の必要条件 = D2 ＋ **DISTINCT registered family が2以上**（external_source_family registry）。
  同一系統（同一OCR/同一編集源/同一出版社系）の複数源は「独立2源」と数えない＝corpus 規模の自己一致防止。
- V+T だけでは confirmed にしない（G_XMODAL_NO_VT_CONFIRMATION）。
- possible 止まりは machine-readable な possible_reason を必須（次アクションを一意化）。

参照: docs/dd_candidates/DD-XMODAL-001_..._v0.4_20260619.md（§1,§2 + v0.3 承継）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set


# ---- enums ------------------------------------------------------------------------
DEC_CONFIRMED = "confirmed"
DEC_POSSIBLE = "possible"
DEC_ABSTAIN = "abstain"

# v0.4 §2 possible_reason（machine-readable）
PR_NO_D2 = "no_d2_evidence"
PR_SINGLE_FAMILY = "single_external_family"
PR_LOW_PROB = "low_label_model_prob"
PR_ABSTAIN_MAJORITY = "abstain_majority"
PR_GRANULARITY = "granularity_mismatch"
PR_TAXONOMY_CONFLICT = "external_taxonomy_conflict"

# external_source_family_registry の family_kind（v0.4 §1）
FAMILY_KINDS = {
    "statute_text", "legal_dictionary", "classification_scheme",
    "commentary_publisher", "ocr_engine", "editorial_source", "court_db",
}


class XmodalValidationError(ValueError):
    pass


# ---- external_source_family registry（v0.4 §1・人手管理の統制レジストリ） ------------
class ExternalSourceFamilyRegistry:
    def __init__(self):
        self._kind: dict = {}  # family_id -> family_kind

    def register(self, family_id: str, family_kind: str) -> None:
        if family_kind not in FAMILY_KINDS:
            raise XmodalValidationError(f"未知の family_kind: {family_kind}")
        self._kind[family_id] = family_kind

    def is_registered(self, family_id: str) -> bool:
        return family_id in self._kind


# ---- D 観測（D0/D1/D2） -----------------------------------------------------------
@dataclass(frozen=True)
class D2Evidence:
    """外部証拠（confirmed に効く唯一の D 観測）。"""
    evidence_id: str
    external_source_family_id: str  # registry を参照
    law_snapshot: str               # G_XMODAL_LAW_SNAPSHOT_REQUIRED
    source_version: str
    valid_at: str


@dataclass
class AgreementInput:
    v_agrees: bool                  # 視覚軸（画像+位置）が一致を支持
    t_agrees: bool                  # テキスト軸（OCR+構造）が一致を支持
    d2_evidences: List[D2Evidence] = field(default_factory=list)
    label_model_prob: Optional[float] = None   # 相関補正後の確率（Snorkel label model）
    abstain_majority: bool = False             # 主要 view が abstain
    granularity_match: bool = True             # 章一致だが unit/bbox 不一致なら False（ストレステスト#3）
    taxonomy_conflict: bool = False            # 外部分類同士の不一致（#4）
    # 確率の中間帯（low_label_model_prob 判定）
    prob_low: float = 0.4
    prob_high: float = 0.8


@dataclass
class AgreementResult:
    decision: str
    possible_reason: Optional[str]
    distinct_registered_families: int


# ---- 判定（v0.4 §1-3・gate 内蔵） --------------------------------------------------
def _distinct_registered_families(d2: List[D2Evidence],
                                  registry: ExternalSourceFamilyRegistry) -> int:
    """confirmed 用: DISTINCT な registered family のみ数える（未登録は independent と見なさない）。"""
    fams: Set[str] = set()
    for e in d2:
        if registry.is_registered(e.external_source_family_id):
            fams.add(e.external_source_family_id)
    return len(fams)


def decide(inp: AgreementInput, registry: ExternalSourceFamilyRegistry) -> AgreementResult:
    """3軸合意の decision と possible_reason を一意に決める。"""
    distinct = _distinct_registered_families(inp.d2_evidences, registry)

    # --- abstain（主要 view が abstain）は最優先で possible/abstain に倒す ---
    # confirmed の必要条件: V/T が一致 ＋ D2 で DISTINCT family ≥ 2 ＋ 確率が中間帯でない ＋
    #                       granularity 一致 ＋ taxonomy 非衝突 ＋ abstain でない
    vt_agree = inp.v_agrees and inp.t_agrees

    confirmed = (
        vt_agree
        and distinct >= 2                       # G_XMODAL_EXTERNAL_EVIDENCE_REQUIRED_FOR_CONFIRMED + FAMILY_REGISTRY
        and not inp.abstain_majority
        and inp.granularity_match
        and not inp.taxonomy_conflict
        and (inp.label_model_prob is None or inp.label_model_prob >= inp.prob_high)
    )
    if confirmed:
        return AgreementResult(DEC_CONFIRMED, None, distinct)

    # --- possible_reason を一意化（v0.4 §2・次アクションを決める優先順） ---
    # 構造的な不一致/衝突 → 確率 → 外部証拠不足 の順で報告
    reason: Optional[str]
    if inp.taxonomy_conflict:
        reason = PR_TAXONOMY_CONFLICT
    elif not inp.granularity_match:
        reason = PR_GRANULARITY
    elif inp.abstain_majority:
        reason = PR_ABSTAIN_MAJORITY
    elif distinct == 0:
        reason = PR_NO_D2                        # G_XMODAL_NO_VT_CONFIRMATION: V+T のみは confirmed 不可
    elif distinct == 1:
        reason = PR_SINGLE_FAMILY                # 外部源が1 family のみ → 独立2源でない
    elif inp.label_model_prob is not None and inp.prob_low <= inp.label_model_prob < inp.prob_high:
        reason = PR_LOW_PROB
    else:
        reason = PR_LOW_PROB                     # D2≥2 だが他要因で未確定（既定）

    # abstain_majority かつ V/T いずれも不支持なら abstain、それ以外は possible
    decision = DEC_ABSTAIN if (inp.abstain_majority and not (inp.v_agrees or inp.t_agrees)) else DEC_POSSIBLE
    return AgreementResult(decision, reason, distinct)
