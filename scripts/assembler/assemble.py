"""Group assertions by provision, detect conflicts, form disputes.

A dispute exists for a target when continuity-claims and change-claims coexist
(or a source self-reports the question as disputed). The assembler records the
disposition as append-only review-events and links opposing assertions via a
representative counter pointer — it never resolves who is right.
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from . import ASSEMBLER_VERSION
from .model import (NormAssertion, ReviewEvent, ResolvedAssertion, Dispute,
                    CONTINUES, CHANGED, QUALIFIED, DISPUTED)


def _dispute_id(target_key: str, member_keys: List[str]) -> str:
    base = target_key + "|" + "|".join(sorted(member_keys))
    return "disp_" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def _opposing_counter(member: NormAssertion,
                      members: List[NormAssertion]) -> Optional[str]:
    """Pick a deterministic representative opposing assertion.

    Continuity claims are opposed by change/qualified/disputed claims and
    vice-versa. We do NOT rank by tier (no auto-resolution); we pick the
    lexicographically smallest opposing assertion_key for determinism.
    """
    side = _side(member.stance)
    opp = [m for m in members if _side(m.stance) and _side(m.stance) != side]
    if not opp:
        return None
    return sorted(m.assertion_key for m in opp)[0]


def _side(stance: str) -> Optional[str]:
    if stance == CONTINUES:
        return "continuity"
    if stance in (CHANGED, QUALIFIED, DISPUTED):
        return "change"
    return None  # neutral / unknown do not take a side


def assemble(assertions: List[NormAssertion], *, now_iso: str
             ) -> Tuple[List[ResolvedAssertion], List[ReviewEvent], List[Dispute]]:
    by_target: Dict[str, List[NormAssertion]] = {}
    for a in assertions:
        by_target.setdefault(a.target_key, []).append(a)

    resolved: List[ResolvedAssertion] = []
    events: List[ReviewEvent] = []
    disputes: List[Dispute] = []

    for target, members in sorted(by_target.items()):
        cont = [m for m in members if m.stance == CONTINUES]
        chng = [m for m in members if m.stance in (CHANGED, QUALIFIED, DISPUTED)]
        selfdisp = [m for m in members if m.stance == DISPUTED]
        # A two-sided dispute needs a continuity claim AND a change/contested
        # claim on the same target. A lone self-`disputed` value with no
        # opposing continuity claim is not fabricated into a dispute.
        is_dispute = bool(cont) and bool(chng)

        dispute_id = None
        if is_dispute:
            member_keys = [m.assertion_key for m in members]
            dispute_id = _dispute_id(target, member_keys)
            cont_side = sorted(m.assertion_key for m in cont)
            chg_side = sorted(m.assertion_key for m in chng)
            tiers = sorted({m.source_tier for m in members})
            basis = _basis(cont, chng)
            disputes.append(Dispute(
                dispute_id=dispute_id, target_key=target,
                member_keys=sorted(member_keys),
                continuity_side=cont_side, change_side=chg_side,
                basis=basis, tiers_involved=tiers,
            ))

        for m in members:
            counter = _opposing_counter(m, members) if is_dispute else None
            in_conflict = is_dispute and _side(m.stance) is not None
            status = "disputed" if in_conflict else "candidate"
            if in_conflict:
                events.append(ReviewEvent(
                    review_id="rev_" + hashlib.sha1(
                        (m.assertion_key + "|" + dispute_id).encode()).hexdigest()[:16],
                    assertion_kind=m.kind,
                    assertion_id=m.assertion_key,
                    new_status="disputed",
                    new_rank="normal",
                    review_basis=(f"assembler: conflicting stances on {target} "
                                  f"({_basis(cont, chng)})"),
                    decided_by=ASSEMBLER_VERSION,
                    decided_at=now_iso,
                ))
            # claim_support: assembler never grants it. Stays False, and the
            # gate below proves the invariant (accepted required, etc.).
            resolved.append(ResolvedAssertion(
                assertion_key=m.assertion_key, kind=m.kind,
                article_path=m.article_path, target_key=target,
                law_work_id=m.law_work_id, value=m.value, stance=m.stance,
                asserted_by_source_type=m.asserted_by_source_type,
                source_tier=m.source_tier, confidence=m.confidence,
                evidence_key=m.evidence_key, current_status=status,
                current_rank="normal", counter_assertion_id=counter,
                dispute_id=dispute_id if in_conflict else None,
                claim_support_eligible=False,
                lawtime_resolved=m.lawtime_resolved,
            ))
    return resolved, events, disputes


def _basis(cont, chng) -> str:
    def tag(m: NormAssertion) -> str:
        return f"T{m.source_tier}:{m.asserted_by_source_type}:{m.value}"
    parts = []
    if cont:
        parts.append("continuity[" + "; ".join(tag(m) for m in cont) + "]")
    if chng:
        parts.append("change[" + "; ".join(tag(m) for m in chng) + "]")
    return " vs ".join(parts)
