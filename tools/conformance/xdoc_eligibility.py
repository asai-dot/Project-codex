"""xdoc_eligibility — DD-XDOC-001 v0.7 §7 の eligibility policy engine（依存ゼロ・純関数）

Phase 0 適合性ハーネス。DD §7-1/7-2/7-3 の表を実行可能に。受入試験 3（shared origin →
ineligible）/ 12（reviewed=none → ineligible）/ 2（purpose×target 別 key）を機械証明する。

priority 解決: 数字大＝高優先。同一 priority 複数該当 → ineligible > hold > eligible。
全非該当 → 7-1 default_eligibility（valid 組合せは hold / invalid 組合せは作成不可）。

参照: docs/dd_candidates/DD-XDOC-001_..._v0.7_20260622.md §7
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:  # フラット実行（dir を sys.path に）でもパッケージ実行でも動く
    from . import xdoc_canonical as _xc
except ImportError:  # pragma: no cover
    import xdoc_canonical as _xc


# ---- enums（§2 抜粋） ---------------------------------------------------------------
ELIG_ELIGIBLE = "eligible"
ELIG_INELIGIBLE = "ineligible"
ELIG_HOLD = "hold"

_ELIG_RANK = {ELIG_INELIGIBLE: 3, ELIG_HOLD: 2, ELIG_ELIGIBLE: 1}  # tie-break 用


# ---- 7-1. purpose_target_compatibility（valid 組合せ・default） --------------------
# (purpose, target) -> default_eligibility。未収載は allowed=false（作成禁止）。
PURPOSE_TARGET_COMPAT: Dict[Tuple[str, str], str] = {
    ("proof_corroboration", "proof"): ELIG_HOLD,
    ("extraction_corroboration", "proof"): ELIG_HOLD,
    ("litlink_candidate", "litlink"): ELIG_HOLD,
    ("edition_resolution", "litid_identity"): ELIG_HOLD,
    ("formobj_variant_candidate", "formobj_variant"): ELIG_HOLD,
    ("frbr_work_candidate", "frbr_work"): ELIG_HOLD,
    ("dedup", "block_ref"): ELIG_HOLD,
}

# ---- 7-2. purpose_positive_reviewed_relations（none/NULL は全 purpose で非該当） ----
PURPOSE_POSITIVE_RELATIONS: Dict[str, set] = {
    "proof_corroboration": {"quote", "reprint", "adaptation", "same_expression"},
    "extraction_corroboration": set(),  # reviewed_relation に依存しない
    "litlink_candidate": {
        "quote", "reprint", "adaptation", "same_expression", "same_topic",
        "near_duplicate", "edition_variant", "template_instance", "figure_reuse",
    },
    "edition_resolution": {"edition_variant"},
    "formobj_variant_candidate": {"template_instance", "common_template"},
    "frbr_work_candidate": {"edition_variant", "same_expression", "adaptation", "reprint"},
    "dedup": {"near_duplicate", "same_expression"},
}

_POSITIVE_TARGETS = {"proof", "litlink", "frbr_work", "litid_identity", "formobj_variant", "block_ref"}
_REVIEWED_REQUIRED_TARGETS = {"litlink", "frbr_work", "litid_identity", "formobj_variant", "block_ref"}


def is_positive(purpose: str, reviewed_relation_type: Optional[str]) -> bool:
    if reviewed_relation_type in (None, "none"):
        return False
    return reviewed_relation_type in PURPOSE_POSITIVE_RELATIONS.get(purpose, set())


class XdocCompatibilityError(ValueError):
    """allowed=false の purpose×target で use_assessment を作成しようとした（§7-1）。"""


# ---- 評価コンテキスト --------------------------------------------------------------
@dataclass
class IndependenceAxis:
    effective_value: str  # independent | shared | partially_shared | unknown
    effective_status: str  # current | stale | invalid


@dataclass
class EligContext:
    evaluation_purpose: str
    target: str
    content_independence: Optional[IndependenceAxis] = None
    observation_independence: Optional[IndependenceAxis] = None
    reviewed_relation_type: Optional[str] = None
    review_state: str = "unreviewed"
    claim_is_absence_or_difference: bool = False
    coverage_complete_for_use_assessment: Optional[bool] = None
    # 任意軸 invalid の global block（priority 110）用。明示 or 軸から導出。
    any_axis_invalid: Optional[bool] = None

    def _exists_invalid(self) -> bool:
        if self.any_axis_invalid is not None:
            return self.any_axis_invalid
        return any(
            ax is not None and ax.effective_status == "invalid"
            for ax in (self.content_independence, self.observation_independence)
        )


@dataclass
class EligResult:
    eligibility: str
    reason_code: str
    priority: Optional[int]  # None = default


# ---- 7-3. eligibility_policy_rule（priority 表） -----------------------------------
# 各 rule: (priority, purpose_match, target_match(set|None), predicate, result, reason)
def _proof(c: EligContext) -> bool:
    return c.evaluation_purpose == "proof_corroboration" and c.target == "proof"


def _rules():
    return [
        (110, lambda c: c._exists_invalid(), ELIG_INELIGIBLE, "INDEPENDENCE_INVALID_GLOBAL"),
        (105, lambda c: _proof(c) and c.observation_independence
              and c.observation_independence.effective_status == "stale",
         ELIG_HOLD, "OBSERVATION_INDEPENDENCE_STALE"),
        (100, lambda c: _proof(c) and c.content_independence
              and c.content_independence.effective_value in ("shared", "partially_shared"),
         ELIG_INELIGIBLE, "CONTENT_NOT_INDEPENDENT"),
        (100, lambda c: _proof(c) and c.content_independence
              and c.content_independence.effective_value == "unknown",
         ELIG_HOLD, "CONTENT_INDEPENDENCE_UNKNOWN"),
        (100, lambda c: _proof(c) and c.observation_independence
              and c.observation_independence.effective_value in ("shared", "partially_shared", "unknown"),
         ELIG_HOLD, "OBSERVATION_NOT_INDEPENDENT_LEGAL"),
        (100, lambda c: _proof(c) and c.content_independence
              and c.content_independence.effective_status == "stale",
         ELIG_HOLD, "CONTENT_INDEPENDENCE_STALE"),
        (90, lambda c: c.claim_is_absence_or_difference
             and c.coverage_complete_for_use_assessment is False,
         ELIG_INELIGIBLE, "COVERAGE_INCOMPLETE"),
        (85, lambda c: c.target in _POSITIVE_TARGETS and c.reviewed_relation_type == "none",
         ELIG_INELIGIBLE, "REVIEWED_RELATION_NONE"),
        (80, lambda c: c.target in _REVIEWED_REQUIRED_TARGETS and c.reviewed_relation_type is None,
         ELIG_INELIGIBLE, "REVIEWED_RELATION_REQUIRED"),
        (70, lambda c: c.evaluation_purpose == "frbr_work_candidate" and c.target == "frbr_work"
             and c.review_state != "reviewed",
         ELIG_HOLD, "HUMAN_REVIEW_REQUIRED"),
        # --- priority 50: eligible 群 ---
        (50, lambda c: _proof(c)
             and c.content_independence and c.content_independence.effective_value == "independent"
             and c.content_independence.effective_status == "current"
             and c.observation_independence and c.observation_independence.effective_value == "independent"
             and c.observation_independence.effective_status == "current"
             and is_positive("proof_corroboration", c.reviewed_relation_type)
             and c.review_state == "reviewed",
         ELIG_ELIGIBLE, "INDEPENDENT_CORROBORATION"),
        (50, lambda c: c.evaluation_purpose == "extraction_corroboration" and c.target == "proof"
             and c.observation_independence
             and c.observation_independence.effective_value in ("independent", "partially_shared")
             and c.observation_independence.effective_status == "current"
             and c.review_state == "reviewed",
         ELIG_ELIGIBLE, "EXTRACTION_CANDIDATE"),
        (50, lambda c: c.evaluation_purpose == "litlink_candidate" and c.target == "litlink"
             and is_positive("litlink_candidate", c.reviewed_relation_type)
             and c.review_state == "reviewed",
         ELIG_ELIGIBLE, "LITLINK_CANDIDATE"),
        (50, lambda c: c.evaluation_purpose == "edition_resolution" and c.target == "litid_identity"
             and is_positive("edition_resolution", c.reviewed_relation_type)
             and c.review_state == "reviewed",
         ELIG_ELIGIBLE, "EDITION_CANDIDATE"),
        (50, lambda c: c.evaluation_purpose == "formobj_variant_candidate" and c.target == "formobj_variant"
             and is_positive("formobj_variant_candidate", c.reviewed_relation_type)
             and c.review_state == "reviewed",
         ELIG_ELIGIBLE, "FORMOBJ_CANDIDATE"),
        (50, lambda c: c.evaluation_purpose == "frbr_work_candidate" and c.target == "frbr_work"
             and is_positive("frbr_work_candidate", c.reviewed_relation_type)
             and c.review_state == "reviewed",
         ELIG_ELIGIBLE, "FRBR_CANDIDATE"),
        (50, lambda c: c.evaluation_purpose == "dedup" and c.target == "block_ref"
             and is_positive("dedup", c.reviewed_relation_type)
             and c.review_state == "reviewed",
         ELIG_ELIGIBLE, "DEDUP_CANDIDATE"),
    ]


def evaluate(c: EligContext) -> EligResult:
    """§7-3 priority 解決で eligibility を決定。allowed=false は作成禁止（例外）。"""
    key = (c.evaluation_purpose, c.target)
    if key not in PURPOSE_TARGET_COMPAT:
        raise XdocCompatibilityError(
            f"allowed=false: ({c.evaluation_purpose}, {c.target}) は作成禁止"
        )

    matched = [(p, res, reason) for (p, pred, res, reason) in _rules() if pred(c)]
    if matched:
        top_priority = max(p for (p, _, _) in matched)
        tier = [(res, reason) for (p, res, reason) in matched if p == top_priority]
        # 同一 priority tie-break: ineligible > hold > eligible
        res, reason = max(tier, key=lambda t: _ELIG_RANK[t[0]])
        return EligResult(res, reason, top_priority)

    # 全非該当 → 7-1 default
    return EligResult(PURPOSE_TARGET_COMPAT[key], "DEFAULT_HOLD", None)


def use_assessment_key_id(alignment_observation_id: str, purpose: str, target: str,
                          policy_id: str, policy_version: str) -> str:
    """§6 logical key（受入試験 2 用）。"""
    return _xc.sha256_hex(_xc.canonical_json({
        "alignment_observation_id": alignment_observation_id,
        "evaluation_purpose": purpose,
        "target": target,
        "policy_id": policy_id,
        "policy_version": policy_version,
    }))
