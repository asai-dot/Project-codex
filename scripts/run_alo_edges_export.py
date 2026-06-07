#!/usr/bin/env python3
"""legal_links → alo_edges 準拠エクスポート（Phase 0, 書込みなし）.

入力 jsonl: 1 行 1 TOC ノード。最低限 {bib_id, ordinal, text}。任意 {pub_year, page}。
出力（out_dir）:
  - alo_edges_export.jsonl        … 文献→条文 interprets エッジ（high/medium のみ）
  - alo_edge_evidence_export.jsonl… 各エッジの根拠（pointer 参照, role=source_field）
  - alo_pointers_export.jsonl     … 抽出スパンの pointer
  - alo_case_ref_candidates.jsonl … 判例引用（canonical case URI 未解決の候補）
  - alo_edges_export_summary.json … 件数サマリ

Usage:
  python scripts/run_alo_edges_export.py --nodes nodes.jsonl --out out_real
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.egov_index import EgovIndex          # noqa: E402
from codex.legal_links import extract_links     # noqa: E402
from codex.alo_edges import transform_node_links  # noqa: E402


def run(nodes_path: str, egov_path: str | None, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    index = EgovIndex.load(egov_path) if egov_path else EgovIndex.load()

    edges, evidence, pointers, cands = [], [], [], []
    n_nodes = skipped_low = 0
    ptr_seen: set = set()
    with open(nodes_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            node = json.loads(line)
            n_nodes += 1
            links = extract_links(node.get("text") or "", index)
            res = transform_node_links(node, links)
            edges.extend(res["edges"])
            evidence.extend(res["edge_evidence"])
            cands.extend(res["case_candidates"])
            skipped_low += res["skipped_low"]
            for p in res["pointers"]:
                if p["pointer_uri"] not in ptr_seen:
                    ptr_seen.add(p["pointer_uri"])
                    pointers.append(p)

    def dump(name, rows):
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        return path

    p_edges = dump("alo_edges_export.jsonl", edges)
    p_evid = dump("alo_edge_evidence_export.jsonl", evidence)
    p_ptr = dump("alo_pointers_export.jsonl", pointers)
    p_cand = dump("alo_case_ref_candidates.jsonl", cands)

    # --- gate 自己検査（DDTOCLEGALREF v0.2 proposed gates）---
    edge_keys = {e["dedup_key"] for e in edges}
    evid_keys = {e["_dedup_key"] for e in evidence}
    rollout = {"initial": 0, "quarantine_sample_required": 0}
    for e in edges:
        rollout[e["rollout_status"]] = rollout.get(e["rollout_status"], 0) + 1

    gates = {
        "gate_toc_edges_have_evidence_pointer": len(edge_keys - evid_keys) == 0,
        "gate_toc_low_tier_not_exported": all(e["weight"] in (1.0, 0.7) for e in edges),
        "gate_toc_no_case_edge_without_canonical_case_uri": len(edges) == 0 or all(
            e["dst_type"] == "statute" for e in edges),  # 判例は edge 化しない
        "gate_toc_pub_year_not_used_as_exact_asof": all(e["valid_from"] is None for e in edges),
        "gate_toc_no_temporal_resolution_before_lawtime_accept": all(
            e["resolved_law_revision_id"] is None and e["temporal_status"] is None
            and e["claim_support_eligible"] is False for e in edges),
        "gate_toc_src_uri_not_marked_canonical_until_resolved": all(
            e["src_uri_status"] == "provisional" and e["canonical_work_uri"] is None
            for e in edges),
        "gate_toc_edge_semantics_quarantined": all(
            e["edge_semantics_status"] == "candidate" for e in edges),
        "gate_toc_assertion_mode_no_vendor_implicit": all(
            e["assertion_mode"] == "implicit" and e["assertion_confidence"] is None
            for e in edges),
        "gate_toc_medium_quarantined": all(
            e["rollout_status"] == "quarantine_sample_required"
            for e in edges if e["weight"] == 0.7),
        "gate_toc_case_candidate_review_required": all(
            c["review_required"] and c.get("matched_case_uri") is None for c in cands),
    }

    summary = {
        "nodes": n_nodes,
        "statute_edges": len(edges),
        "edge_evidence": len(evidence),
        "pointers": len(pointers),
        "case_ref_candidates": len(cands),
        "skipped_low_conf": skipped_low,
        "edge_type_breakdown": {"interprets": len(edges)},
        "rollout_breakdown": rollout,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "schema_version": "DDTOCLEGALREF v0.2",
    }
    orphan_edges = 0 if gates["gate_toc_edges_have_evidence_pointer"] else 1
    with open(os.path.join(out_dir, "alo_edges_export_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    summary["_paths"] = [p_edges, p_evid, p_ptr, p_cand]
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nodes", required=True)
    ap.add_argument("--egov", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    s = run(args.nodes, args.egov, args.out)
    print(json.dumps({k: v for k, v in s.items() if k != "_paths"}, ensure_ascii=False, indent=2))
    assert s["all_gates_pass"], f"gate violation: {[k for k,v in s['gates'].items() if not v]}"
    print("ALL GATES: PASS")


if __name__ == "__main__":
    main()
