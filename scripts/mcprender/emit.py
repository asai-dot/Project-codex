"""Emit MCP render payloads + safe-output gates (DD §5)."""
from __future__ import annotations

import json
import os
import re
from typing import List

# Phrases that would constitute an unhedged substantive assertion in the
# renderer's own voice. The safe summary must never contain these as a bare
# verdict (they may appear only inside an attributed/【出典】 clause).
ASSERTIVE_BANNED = [
    "旧法理は現在も有効です",
    "実質的に変更されました。",
    "解釈は変わりました。",
    "適用されます。",
]


class GateFailure(AssertionError):
    pass


def run_gates(views: List[dict]) -> dict:
    results = {}

    def gate(name, ok, detail=""):
        results[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            raise GateFailure(f"{name}: {detail}")

    # every view declares assertive output disallowed
    bad = [v["target"] for v in views if v.get("assertive_output_allowed")]
    gate("gate_no_assertive_output_flag", not bad, f"{bad[:5]}")

    # disputed targets must render both sides (>=2 claims, both stances present)
    incomplete = []
    for v in views:
        if v["disposition"] == "disputed":
            stances = {c["stance"] for c in v["claims"]}
            has_cont = "continues" in stances
            has_chg = bool({"changed", "qualified", "disputed"} & stances)
            if not (v["both_sides_required"] and has_cont and has_chg
                    and len(v["claims"]) >= 2):
                incomplete.append(v["target"])
    gate("gate_disputed_renders_both_sides", not incomplete, f"{incomplete[:5]}")

    # no claim is framed as relied-upon unless claim_support_eligible (assembler
    # never grants it -> every usage must be the cautious label)
    relied = []
    for v in views:
        for c in v["claims"]:
            if c["usage"] == "参考提示可":
                relied.append(v["target"])
    gate("gate_no_relied_upon_without_claim_support", not relied,
         f"claim_support framing leaked: {relied[:5]}")

    # the safe summary must not contain a banned bare assertion
    asserted = []
    for v in views:
        s = v["safe_summary"]
        if any(p in s for p in ASSERTIVE_BANNED):
            asserted.append(v["target"])
    gate("gate_summary_not_assertive", not asserted, f"{asserted[:5]}")

    # every substantive claim line carries a source attribution + stance
    unattributed = []
    for v in views:
        for c in v["claims"]:
            if not c.get("source") or not c.get("stance"):
                unattributed.append(v["target"])
    gate("gate_every_claim_attributed", not unattributed, f"{unattributed[:5]}")

    # unknown is never used as a basis: a disputed dispute_basis must not be the
    # sole content; unknown-stance claims are allowed but flagged 未確認
    return results


def write_artifacts(views: List[dict], out_dir: str, run_id: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"mcp_provision_views_{run_id}.jsonl"),
              "w", encoding="utf-8") as f:
        for v in views:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")
    md = "\n\n".join(v["markdown"] for v in views)
    with open(os.path.join(out_dir, f"mcp_provision_views_{run_id}.md"),
              "w", encoding="utf-8") as f:
        f.write(md + "\n")
    gates = run_gates(views)
    summary = {
        "run_id": run_id,
        "provisions": len(views),
        "disputed": sum(1 for v in views if v["disposition"] == "disputed"),
        "gates": gates,
        "all_gates_pass": all(g["pass"] for g in gates.values()),
        "db_writes": 0,
    }
    with open(os.path.join(out_dir, f"mcp_render_{run_id}_summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary
