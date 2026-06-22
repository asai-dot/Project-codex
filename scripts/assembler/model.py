"""Normalized assertion model + stance maps for dispute detection."""
from __future__ import annotations

import dataclasses
from typing import Optional

# ---------------------------------------------------------------------------
# stance: the coarse projection used to detect agreement/disagreement about
# whether a provision's substantive meaning / doctrine persisted.
#   continues  — the meaning/doctrine carried over (no substantive change)
#   changed    — the meaning/doctrine changed / was displaced
#   qualified  — partially limited/distinguished (a soft break in continuity)
#   neutral    — merely cited/considered; no continuity signal
#   disputed   — the source itself reports the question as contested
#   unknown    — not determinable
# ---------------------------------------------------------------------------
CONTINUES, CHANGED, QUALIFIED, NEUTRAL, DISPUTED, UNKNOWN = (
    "continues", "changed", "qualified", "neutral", "disputed", "unknown")

# DD §2.1 substantive_change_type -> stance
CHANGE_TYPE_STANCE = {
    "no_substantive_change": CONTINUES,
    "wording_clarification": CONTINUES,
    "scope_expansion": CHANGED,
    "scope_reduction": CHANGED,
    "requirement_added": CHANGED,
    "requirement_removed": CHANGED,
    "requirement_changed": CHANGED,
    "effect_changed": CHANGED,
    "subject_changed": CHANGED,
    "procedure_changed": CHANGED,
    "efficacy_change": CHANGED,
    "substantive_change_unspecified": CHANGED,
    "disputed": DISPUTED,
    "unknown": UNKNOWN,
}

# DD §2.2 interpretation_transition_type -> stance
TRANSITION_TYPE_STANCE = {
    "interpretation_continues": CONTINUES,
    "interpretation_discontinued": CHANGED,
    "interpretation_modified": QUALIFIED,
    "interpretation_newly_established": CHANGED,
    "interpretation_disputed": DISPUTED,
    "unknown": UNKNOWN,
}

# DD §2.6 treatment_relation -> stance (when a treatment is bound to a provision)
TREATMENT_STANCE = {
    "followed": CONTINUES, "applied": CONTINUES, "approved": CONTINUES,
    "relied_upon": CONTINUES,
    "cited": NEUTRAL, "considered": NEUTRAL, "explained": NEUTRAL,
    "distinguished": QUALIFIED, "limited": QUALIFIED, "questioned": QUALIFIED,
    "criticized": QUALIFIED, "called_into_doubt": QUALIFIED,
    "declined_to_extend": QUALIFIED, "followed_with_reservations": QUALIFIED,
    "not_applied": QUALIFIED,
    "overruled": CHANGED, "abrogated": CHANGED, "disapproved": CHANGED,
    "superseded_by_statute": CHANGED,
}

STANCE_BY_SOURCE = {
    "change_type": CHANGE_TYPE_STANCE,
    "transition_type": TRANSITION_TYPE_STANCE,
    "treatment_relation": TREATMENT_STANCE,
}


def stance_of(stance_source: str, value: str) -> str:
    return STANCE_BY_SOURCE.get(stance_source, {}).get(value, UNKNOWN)


def article_root(article_path: str) -> str:
    """Group key: article without paragraph/item (art:415:para:1 -> art:415)."""
    if not article_path:
        return ""
    return article_path.split(":para:", 1)[0].split(":item:", 1)[0]


@dataclasses.dataclass
class NormAssertion:
    """Producer-agnostic normalized assertion fed to the assembler."""
    assertion_key: str
    kind: str                      # substantive_change / interpretation_transition / old_law_survival
    article_path: str
    law_work_id: Optional[str]
    stance_source: str             # change_type / transition_type / treatment_relation
    value: str                     # the controlled-vocab value
    asserted_by_source_type: str
    source_tier: int
    evidence_key: Optional[str]
    confidence: str
    doctrine_label: Optional[str] = None
    lawtime_resolved: bool = False  # set true only when from/to revision resolves in lawtime

    @property
    def stance(self) -> str:
        return stance_of(self.stance_source, self.value)

    @property
    def target_key(self) -> str:
        return article_root(self.article_path)


@dataclasses.dataclass
class ReviewEvent:
    """T6 alo_law_assertion_review_event (append-only)."""
    review_id: str
    assertion_kind: str
    assertion_id: str              # assertion_key
    new_status: str                # candidate/reviewed/accepted/disputed/deprecated
    new_rank: Optional[str]
    review_basis: str              # machine-readable reason (Wikidata P2241/P7452)
    decided_by: str
    decided_at: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class ResolvedAssertion:
    """An assertion with its assembler-computed current disposition."""
    assertion_key: str
    kind: str
    article_path: str
    target_key: str
    law_work_id: Optional[str]
    value: str
    stance: str
    asserted_by_source_type: str
    source_tier: int
    confidence: str
    evidence_key: Optional[str]
    current_status: str
    current_rank: str
    counter_assertion_id: Optional[str]
    dispute_id: Optional[str]
    claim_support_eligible: bool
    lawtime_resolved: bool

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class Dispute:
    dispute_id: str
    target_key: str
    member_keys: list
    continuity_side: list          # assertion_keys claiming continues
    change_side: list              # assertion_keys claiming changed/qualified/disputed
    basis: str                     # human/machine summary
    tiers_involved: list

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
