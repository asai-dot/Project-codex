"""Emit assembler artifacts + self-check gates (DD §4)."""
from __future__ import annotations

import json
import os
from typing import List

from .model import ResolvedAssertion, ReviewEvent, Dispute


class GateFailure(AssertionError):
    pass


def run_gates(resolved: List[ResolvedAssertion], events: List[ReviewEvent],
              disputes: List[Dispute]) -> dict:
    results = {}

    def gate(name: str, ok: bool, detail: str = "") -> None:
        results[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            raise GateFailure(f"{name}: {detail}")

    R = [r.to_dict() for r in resolved]

    # DD §4 disputed_blocks_claim
    bad = [r["assertion_key"][:8] for r in R
           if r["counter_assertion_id"] and
           (r["claim_support_eligible"] or r["current_status"] != "disputed")]
    gate("gate_disputed_blocks_claim", not bad, f"{bad[:5]}")

    # DD §4 claim_support_requires_accepted (full condition)
    leak = [r["assertion_key"][:8] for r in R if r["claim_support_eligible"] and not (
        r["current_status"] == "accepted" and not r["counter_assertion_id"]
        and r["lawtime_resolved"])]
    gate("gate_claim_support_requires_accepted", not leak, f"{leak[:5]}")

    # assembler must not grant accepted (that needs a human review-event)
    acc = [e.assertion_id[:8] for e in events if e.new_status == "accepted"]
    gate("gate_assembler_never_accepts", not acc, f"{acc[:5]}")

    # no self-counter
    selfc = [r["assertion_key"][:8] for r in R
             if r["counter_assertion_id"] == r["assertion_key"]]
    gate("gate_no_self_counter", not selfc, f"{selfc[:5]}")

    # every dispute has both sides nonempty
    onesided = [d.dispute_id for d in disputes
                if not d.continuity_side or not d.change_side]
    gate("gate_dispute_two_sided", not onesided, f"{onesided[:5]}")

    # review events carry a machine-readable basis
    nobasis = [e.review_id for e in events if not e.review_basis]
    gate("gate_review_event_has_basis", not nobasis, f"{nobasis[:5]}")

    # disputed assertions reference a dispute and a counter
    incoh = [r["assertion_key"][:8] for r in R
             if r["current_status"] == "disputed" and
             (not r["dispute_id"] or not r["counter_assertion_id"])]
    gate("gate_disputed_has_dispute_and_counter", not incoh, f"{incoh[:5]}")

    return results


def write_artifacts(resolved: List[ResolvedAssertion], events: List[ReviewEvent],
                    disputes: List[Dispute], out_dir: str, run_id: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)

    def dump(name, rows):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    dump(f"resolved_assertions_{run_id}.jsonl", resolved)
    dump(f"assertion_review_events_{run_id}.jsonl", events)
    dump(f"disputes_{run_id}.jsonl", disputes)

    gates = run_gates(resolved, events, disputes)
    status_counts: dict = {}
    for r in resolved:
        status_counts[r.current_status] = status_counts.get(r.current_status, 0) + 1
    summary = {
        "run_id": run_id,
        "assertions": len(resolved),
        "disputes": len(disputes),
        "review_events": len(events),
        "by_status": dict(sorted(status_counts.items())),
        "claim_support_eligible_count": sum(
            1 for r in resolved if r.claim_support_eligible),
        "gates": gates,
        "all_gates_pass": all(g["pass"] for g in gates.values()),
        "db_writes": 0,
    }
    with open(os.path.join(out_dir, f"assemble_{run_id}_summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary
