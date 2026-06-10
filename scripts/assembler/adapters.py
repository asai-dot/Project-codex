"""Adapters: producer JSONL rows -> NormAssertion.

Keeps the assembler producer-agnostic. Each producer's output schema is mapped
into the normalized stance-bearing form.
"""
from __future__ import annotations

from typing import List

from .model import NormAssertion


def from_drafter_rows(rows: List[dict]) -> List[NormAssertion]:
    """drafterintent `drafter_substantive_assertions_*.jsonl` rows."""
    out = []
    for r in rows:
        out.append(NormAssertion(
            assertion_key=r["assertion_key"],
            kind="substantive_change",
            article_path=r["article_path"],
            law_work_id=r.get("law_work_id"),
            stance_source="change_type",
            value=r["change_type"],
            asserted_by_source_type=r["asserted_by_source_type"],
            source_tier=int(r["source_tier"]),
            evidence_key=r.get("evidence_key"),
            confidence=r.get("confidence", "low"),
            doctrine_label=None,
            lawtime_resolved=bool(r.get("lawtime_resolved", False)),
        ))
    return out


def from_interpretation_rows(rows: List[dict]) -> List[NormAssertion]:
    """Pre-normalized interpretation_transition rows (court/scholar view of a
    provision's doctrine). This is the shape Phase-4 emits once a treatment is
    bound to a provision/doctrine target by a curator.

    Required: assertion_key, article_path, transition_type, asserted_by_source_type,
    source_tier. Optional: law_work_id, evidence_key, confidence, doctrine_label.
    """
    out = []
    for r in rows:
        out.append(NormAssertion(
            assertion_key=r["assertion_key"],
            kind="interpretation_transition",
            article_path=r["article_path"],
            law_work_id=r.get("law_work_id"),
            stance_source="transition_type",
            value=r["transition_type"],
            asserted_by_source_type=r["asserted_by_source_type"],
            source_tier=int(r["source_tier"]),
            evidence_key=r.get("evidence_key"),
            confidence=r.get("confidence", "low"),
            doctrine_label=r.get("doctrine_label"),
            lawtime_resolved=bool(r.get("lawtime_resolved", False)),
        ))
    return out


def from_treatment_rows(rows: List[dict], bindings: dict) -> List[NormAssertion]:
    """casetreatment `case_treatment_candidates_*.jsonl` rows + a target binding.

    casetreatment is case->case centric, so a treatment becomes an
    interpretation assertion about a PROVISION only when a curator binds it to
    a target (dedup_key -> {article_path, law_work_id?, doctrine_label?}).
    Unbound treatments are skipped (they are not provision-level claims).
    """
    out = []
    for r in rows:
        b = bindings.get(r["dedup_key"])
        if not b:
            continue
        out.append(NormAssertion(
            assertion_key=r["dedup_key"],
            kind="interpretation_transition",
            article_path=b["article_path"],
            law_work_id=b.get("law_work_id"),
            stance_source="treatment_relation",
            value=r["treatment_relation"],
            asserted_by_source_type=r["source_type"],
            source_tier={"court": 3, "scholar": 4, "treatise": 4,
                         "practitioner": 4}.get(r["source_type"], 4),
            evidence_key=r["dedup_key"],
            confidence=r.get("confidence", "low"),
            doctrine_label=b.get("doctrine_label"),
            lawtime_resolved=bool(b.get("lawtime_resolved", False)),
        ))
    return out
