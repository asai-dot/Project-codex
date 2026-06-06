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

    # Gate-5 自己検査: 全エッジに evidence が付くこと
    edge_keys = {(e["src_uri"], e["dst_uri"], e["edge_type"], e["valid_from"]) for e in edges}
    evid_keys = {(e["_src_uri"], e["_dst_uri"], e["_edge_type"], e["_valid_from"]) for e in evidence}
    orphan_edges = len(edge_keys - evid_keys)

    summary = {
        "nodes": n_nodes,
        "statute_edges": len(edges),
        "edge_evidence": len(evidence),
        "pointers": len(pointers),
        "case_ref_candidates": len(cands),
        "skipped_low_conf": skipped_low,
        "edge_type_breakdown": {"interprets": len(edges)},
        "gate5_orphan_edges": orphan_edges,
        "constraints_enforced": [
            "edge_type∈{interprets,evaluates}",
            "assertion_mode=vendor_implicit",
            "assertion_confidence=NULL (llm only)",
            "weight=tier(high1.0/med0.7); low excluded",
            "Gate-5 evidence required",
        ],
    }
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
    assert s["gate5_orphan_edges"] == 0, "Gate-5 violation: edge without evidence"
    print("Gate-5: PASS (0 orphan edges)")


if __name__ == "__main__":
    main()
