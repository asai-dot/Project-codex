#!/usr/bin/env python3
"""P0→P1 ターンキー: silver-1 → silver-2 → stage-write(dry-run) を順に回す.

SILVER-RESOLUTION-KICKOFF v0.1.1 整合. すべて read-only / dry-run.
stage-write は **既定 dry-run**（owner ratify 後に別途 --apply で確定）.

例:
  python3 tools/silver_resolve/run_p0.py \
    --lic-edges lic.jsonl --pub-index pub.jsonl --canon-index canon.jsonl \
    --norm-dict journal_norm.json --authority-snapshot authority_snapshot.json \
    --toc-nodes toc_nodes.jsonl --toc-edges toc_edges.jsonl --hyoshaku hyoshaku.jsonl \
    --out out/p0_20260619

silver-1 か silver-2 のどちらか一方だけでも可（対応する入力を渡したレーンのみ実行）.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import silver_cite_id as s1
import silver_stage_write as sw
import silver_toc_section as s2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P0→P1 ターンキー (read-only / dry-run)")
    # silver-1
    ap.add_argument("--lic-edges", type=Path)
    ap.add_argument("--pub-index", type=Path)
    ap.add_argument("--canon-index", type=Path)
    ap.add_argument("--norm-dict", type=Path)
    ap.add_argument("--authority-snapshot", type=Path)
    # silver-2
    ap.add_argument("--toc-nodes", type=Path)
    ap.add_argument("--toc-edges", type=Path)
    ap.add_argument("--hyoshaku", type=Path)
    # 共通
    ap.add_argument("--field-map", type=Path)
    ap.add_argument("--policy", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    out1 = a.out / "silver1"
    out2 = a.out / "silver2"
    staging = a.out / "silver_staging"
    cite_cand = out1 / "silver_cite_resolution_candidates.jsonl"
    sec_cand = out2 / "silver_toc_section_candidates.jsonl"
    cooc_cand = out2 / "silver_issue_cooccurrence_candidates.jsonl"

    def opt(flag, val):
        return [flag, str(val)] if val else []

    ran = []
    if a.lic_edges and a.pub_index:
        print("== silver-1 ==")
        s1.main(["--lic-edges", str(a.lic_edges), "--pub-index", str(a.pub_index),
                 *opt("--canon-index", a.canon_index), *opt("--norm-dict", a.norm_dict),
                 *opt("--authority-snapshot", a.authority_snapshot), *opt("--field-map", a.field_map),
                 "--out", str(out1)])
        ran.append("silver-1")
    if a.toc_nodes and a.toc_edges:
        print("== silver-2 ==")
        s2.main(["--toc-nodes", str(a.toc_nodes), "--toc-edges", str(a.toc_edges),
                 *opt("--hyoshaku", a.hyoshaku), *opt("--field-map", a.field_map), "--out", str(out2)])
        ran.append("silver-2")

    print("== P1 stage-write (dry-run) ==")
    sw.main([*( ["--cite-candidates", str(cite_cand)] if cite_cand.exists() else [] ),
             *( ["--section-candidates", str(sec_cand)] if sec_cand.exists() else [] ),
             *( ["--cooc-candidates", str(cooc_cand)] if cooc_cand.exists() else [] ),
             *opt("--policy", a.policy), "--staging-dir", str(staging)])

    print(f"\n[run_p0] ran={ran or ['(none)']}  reports under {a.out}")
    print("[run_p0] stage-write は dry-run. owner ratify 後に silver_stage_write.py --apply で確定.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
