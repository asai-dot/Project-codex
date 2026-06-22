"""Emit JSONL artifacts + producer self-check gates (DD-LAWSUBTRANS-001 §4).

DB writes: none. Output contract mirrors T1 ``alo_law_textual_delta``.
"""
from __future__ import annotations

import json
from typing import List

from .model import DeltaRecord
from .align import RENUMBER_SIM, RELOCATE_SIM, _num_main

# Fields that would smuggle substantive judgement into a textual observation.
FORBIDDEN_SUBSTANTIVE_FIELDS = {
    "substantive_change_type", "change_type", "interpretation",
    "substantive_status", "claim_support_eligible", "assertion_status",
    "temporal_reach", "source_tier",
}


class GateFailure(AssertionError):
    pass


def run_gates(records: List[DeltaRecord]) -> dict:
    results = {}

    def gate(name: str, ok: bool, detail: str = "") -> None:
        results[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            raise GateFailure(f"{name}: {detail}")

    rows = [r.to_dict() for r in records]

    bad_kind = [r["article_path"] for r in rows
                if r["delta_kind"] not in DeltaRecord.DELTA_KIND_DOMAIN]
    gate("gate_delta_kind_domain", not bad_kind, f"out-of-domain: {bad_kind[:5]}")

    leaked = sorted({k for r in rows for k in r} & FORBIDDEN_SUBSTANTIVE_FIELDS)
    gate("gate_no_substantive_fields", not leaked,
         f"textual delta must not carry substantive fields: {leaked}")

    missing = [r["article_path"] for r in rows
               if not r["detector_version"] or not r["source_snapshot_id"]
               or not r["from_law_revision_id"] or not r["to_law_revision_id"]]
    gate("gate_rows_have_provenance", not missing, f"missing provenance: {missing[:5]}")

    # renumber must be justified by near-identical content OR a coherent
    # block shift (>=2 renumber rows sharing the same numeric offset).
    renum_rows = [r for r in rows if r["delta_kind"] == "renumber"]
    offsets: dict = {}
    for r in renum_rows:
        if r["counterpart_paths"]:
            om = _num_main(r["article_path"].split(":", 1)[1])
            nm = _num_main(r["counterpart_paths"][0].split(":", 1)[1])
            if om is not None and nm is not None:
                offsets[nm - om] = offsets.get(nm - om, 0) + 1
    weak_renum = []
    for r in renum_rows:
        sim = r["similarity"]
        if sim is None or sim < RELOCATE_SIM:
            weak_renum.append(r["article_path"])
            continue
        if sim >= RENUMBER_SIM:
            continue
        om = _num_main(r["article_path"].split(":", 1)[1]) if ":" in r["article_path"] else None
        nm = (_num_main(r["counterpart_paths"][0].split(":", 1)[1])
              if r["counterpart_paths"] else None)
        if om is None or nm is None or offsets.get(nm - om, 0) < 2:
            weak_renum.append(r["article_path"])
    gate("gate_renumber_justified", not weak_renum,
         f"renumber lacks high similarity or block-shift basis: {weak_renum[:5]}")

    drift = [r["article_path"] for r in rows
             if r["delta_kind"] == "no_change" and r["text_changed"]]
    gate("gate_no_change_rows_text_unchanged", not drift, f"no_change but changed: {drift[:5]}")

    multi = [r["article_path"] for r in rows
             if r["delta_kind"] in ("split", "join") and len(r["counterpart_paths"]) < 2]
    gate("gate_split_join_have_counterparts", not multi,
         f"split/join needs >=2 counterparts: {multi[:5]}")

    return results


def write_artifacts(records: List[DeltaRecord], out_dir: str, run_id: str) -> dict:
    import os
    os.makedirs(out_dir, exist_ok=True)
    rows_path = os.path.join(out_dir, f"law_textual_delta_{run_id}.jsonl")
    with open(rows_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
    gates = run_gates(records)
    kinds: dict = {}
    for r in records:
        kinds[r.delta_kind] = kinds.get(r.delta_kind, 0) + 1
    summary = {
        "run_id": run_id,
        "rows": len(records),
        "by_kind": dict(sorted(kinds.items())),
        "gates": gates,
        "all_gates_pass": all(g["pass"] for g in gates.values()),
        "db_writes": 0,
    }
    summary_path = os.path.join(out_dir, f"law_textual_delta_{run_id}_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary
