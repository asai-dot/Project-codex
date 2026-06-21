"""Emit treatment-candidate JSONL + self-check gates (DD-LAWSUBTRANS-001 §4/§5)."""
from __future__ import annotations

import json
import os
from typing import List

from .extract import TreatmentCandidate
from .patterns import TREATMENT_DOMAIN, STRONG_ONLY


class GateFailure(AssertionError):
    pass


def run_gates(cands: List[TreatmentCandidate]) -> dict:
    results = {}

    def gate(name: str, ok: bool, detail: str = "") -> None:
        results[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            raise GateFailure(f"{name}: {detail}")

    rows = [c.to_dict() for c in cands]

    bad = [r["dedup_key"][:8] for r in rows
           if r["assertion_status"] != "candidate"]
    gate("gate_treatment_all_candidate_status", not bad,
         f"non-candidate rows: {bad[:5]}")

    cs = [r["dedup_key"][:8] for r in rows if r["claim_support_eligible"]]
    gate("gate_treatment_no_claim_support", not cs,
         f"claim_support leaked: {cs[:5]}")

    dom = [r["treatment_relation"] for r in rows
           if r["treatment_relation"] not in TREATMENT_DOMAIN]
    gate("gate_treatment_domain", not dom, f"out-of-domain: {sorted(set(dom))[:5]}")

    noev = [r["dedup_key"][:8] for r in rows
            if not r["quoted_text"] or r["span_end"] <= r["span_start"]]
    gate("gate_treatment_has_evidence_span", not noev,
         f"missing evidence span: {noev[:5]}")

    strong = [r["dedup_key"][:8] for r in rows
              if r["treatment_relation"] in STRONG_ONLY and not r["cue_text"]]
    gate("gate_strong_treatment_requires_cue", not strong,
         f"strong treatment without explicit cue: {strong[:5]}")

    hi = [r["dedup_key"][:8] for r in rows if r["confidence"] == "high"]
    gate("gate_no_high_confidence_from_rules", not hi,
         f"rule-based extraction must not claim high confidence: {hi[:5]}")

    return results


def write_artifacts(cands: List[TreatmentCandidate], out_dir: str,
                    run_id: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    rows_path = os.path.join(out_dir, f"case_treatment_candidates_{run_id}.jsonl")
    with open(rows_path, "w", encoding="utf-8") as f:
        for c in cands:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    gates = run_gates(cands)
    by_rel: dict = {}
    for c in cands:
        by_rel[c.treatment_relation] = by_rel.get(c.treatment_relation, 0) + 1
    summary = {
        "run_id": run_id,
        "rows": len(cands),
        "by_treatment": dict(sorted(by_rel.items())),
        "gates": gates,
        "all_gates_pass": all(g["pass"] for g in gates.values()),
        "db_writes": 0,
    }
    with open(os.path.join(out_dir, f"case_treatment_candidates_{run_id}_summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary
