"""Emit drafter-intent JSONL (T2 + T5) and self-check gates (DD §4/§5)."""
from __future__ import annotations

import json
import os
from typing import List

from .extract import Evidence, SubstantiveAssertion
from .patterns import CHANGE_TYPE_DOMAIN


class GateFailure(AssertionError):
    pass


def run_gates(evidences: List[Evidence],
              assertions: List[SubstantiveAssertion]) -> dict:
    results = {}

    def gate(name: str, ok: bool, detail: str = "") -> None:
        results[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            raise GateFailure(f"{name}: {detail}")

    A = [a.to_dict() for a in assertions]
    E = {e.evidence_key: e.to_dict() for e in evidences}

    bad = [a["assertion_key"][:8] for a in A if a["assertion_status"] != "candidate"]
    gate("gate_drafter_all_candidate_status", not bad, f"{bad[:5]}")

    cs = [a["assertion_key"][:8] for a in A if a["claim_support_eligible"]]
    gate("gate_drafter_no_claim_support", not cs, f"claim_support leaked: {cs[:5]}")

    # tier-2 only; never tier 1 (official_legal_data lives in DD-LAWTIME)
    t = [a["assertion_key"][:8] for a in A
         if a["source_tier"] != 2 or a["asserted_by_source_type"] not in
         ("legislative_drafter", "ministry_commentary", "legislative_record")]
    gate("gate_drafter_source_tier_2", not t, f"non-tier-2 drafter source: {t[:5]}")

    dom = [a["change_type"] for a in A if a["change_type"] not in CHANGE_TYPE_DOMAIN]
    gate("gate_drafter_change_type_domain", not dom, f"{sorted(set(dom))[:5]}")

    # every assertion must point at evidence with a real span + quote
    noev = []
    for a in A:
        e = E.get(a["evidence_key"])
        if (e is None or not e["quoted_text"] or not e["source_span_hash"]):
            noev.append(a["assertion_key"][:8])
    gate("gate_drafter_assertion_has_evidence", not noev, f"{noev[:5]}")

    # every assertion must carry a cue (no fabricated change_type from a bare ref)
    nocue = [a["assertion_key"][:8] for a in A if not a["cue_text"]]
    gate("gate_drafter_change_requires_cue", not nocue, f"{nocue[:5]}")

    hi = [a["assertion_key"][:8] for a in A if a["confidence"] == "high"]
    gate("gate_no_high_confidence_from_rules", not hi, f"{hi[:5]}")

    # every assertion targets an article path
    noart = [a["assertion_key"][:8] for a in A if not a["article_path"]]
    gate("gate_drafter_assertion_has_article_path", not noart, f"{noart[:5]}")

    return results


def write_artifacts(evidences: List[Evidence],
                    assertions: List[SubstantiveAssertion],
                    out_dir: str, run_id: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"drafter_evidence_{run_id}.jsonl"),
              "w", encoding="utf-8") as f:
        for e in evidences:
            f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")
    with open(os.path.join(out_dir, f"drafter_substantive_assertions_{run_id}.jsonl"),
              "w", encoding="utf-8") as f:
        for a in assertions:
            f.write(json.dumps(a.to_dict(), ensure_ascii=False) + "\n")
    gates = run_gates(evidences, assertions)
    by_type: dict = {}
    for a in assertions:
        by_type[a.change_type] = by_type.get(a.change_type, 0) + 1
    summary = {
        "run_id": run_id,
        "evidence_rows": len(evidences),
        "assertion_rows": len(assertions),
        "by_change_type": dict(sorted(by_type.items())),
        "gates": gates,
        "all_gates_pass": all(g["pass"] for g in gates.values()),
        "db_writes": 0,
    }
    with open(os.path.join(out_dir, f"drafter_intent_{run_id}_summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary
