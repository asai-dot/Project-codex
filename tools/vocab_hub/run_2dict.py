#!/usr/bin/env python3
"""ワンショット: 有斐閣＋学陽 で 2辞書 Hub dry-run を回し, 0.5/0.6/0.7 を比較表示する.

Box のゴールドを自動探索するので、引数なしで動く:
    python3 tools/vocab_hub/run_2dict.py

read-only / DBに書かない. 出力(0.6版 report)は既定 ~/hub_2dict/ に保存し、比較表は画面に出す.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import adapt_hourei as ah
import build_hub_dryrun as bh

CANDIDATE_ROOTS = ["Library/CloudStorage", "Box"]


def find_one(name: str, override=None):
    if override:
        return Path(override)
    for root in CANDIDATE_ROOTS:
        base = Path.home() / root
        if base.exists():
            for p in base.rglob(name):
                return p
    return None


def cross_dict_hubs(memberships) -> int:
    """辞書をまたいで統合された hub 数 (member の scheme_id が 2 種以上)."""
    by_hub: dict = {}
    for m in memberships:
        by_hub.setdefault(m["hub_id"], set()).add(str(m.get("scheme_id")))
    return sum(1 for s in by_hub.values() if len(s) >= 2)


def _yuhikaku_reading_map(y_terms):
    """有斐閣の normalized_pref -> reading マップ (reading 補完③用)."""
    m = {}
    for t in y_terms:
        np = bh.norm_pref(t.get("normalized_pref") or t.get("pref_label") or "")
        r = bh.norm_reading(t.get("reading", ""))
        if np and r and np not in m:
            m[np] = t.get("reading", "")  # 正規化前の表記を保持
    return m


def load_terms(yt, yl, he):
    terms = list(bh.read_jsonl(yt))
    n_y = len(terms)
    if yl:
        bh.attach_definitions(terms, bh.read_jsonl(yl))
    n_h = 0
    if he:
        y_rmap = _yuhikaku_reading_map(terms)
        entries = [json.loads(x) for x in Path(he).read_text(encoding="utf-8").splitlines() if x.strip()]
        hterms = ah.adapt(entries, "hourei_yougo_jiten_11", 102, yuhikaku_reading_map=y_rmap)
        terms.extend(hterms)
        n_h = len(hterms)
    return terms, n_y, n_h


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="2辞書(有斐閣+学陽) Hub dry-run ワンショット")
    ap.add_argument("--yuhikaku-terms", default=None)
    ap.add_argument("--yuhikaku-labels", default=None)
    ap.add_argument("--hourei-entries", default=None)
    ap.add_argument("--out", default=str(Path.home() / "hub_2dict"))
    ap.add_argument("--thresholds", default="0.5,0.6,0.7")
    ap.add_argument("--quality-filter", action="store_true", default=False,
                    help="空定義/短定義を anchor 非適格としてフラグ付け (P0.5 clean subset モード)")
    a = ap.parse_args(argv)

    yt = find_one("yuhikaku_legal_dict_terms_stg_v3.jsonl", a.yuhikaku_terms)
    yl = find_one("yuhikaku_legal_dict_labels_stg_v3.jsonl", a.yuhikaku_labels)
    he = find_one("hourei_all_entries_v0.2_20260612.jsonl", a.hourei_entries)
    print(f"[run_2dict] 有斐閣 terms : {yt}")
    print(f"[run_2dict] 有斐閣 labels: {yl}")
    print(f"[run_2dict] 学陽 entries : {he}")
    if not yt:
        print("ERROR: 有斐閣 terms が見つかりません。--yuhikaku-terms で明示してください。", file=sys.stderr)
        return 2

    terms, n_y, n_h = load_terms(yt, yl, he)
    print(f"[run_2dict] terms: 有斐閣={n_y} 学陽={n_h} 計={len(terms)}\n")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    thresholds = [float(x) for x in a.thresholds.split(",")]
    qf = a.quality_filter
    rows = []
    for thr in thresholds:
        hubs, mem, stats = bh.build_hubs(terms, thr, quality_filter=qf)
        rows.append((thr, stats, cross_dict_hubs(mem)))
        if abs(thr - 0.6) < 1e-9:
            with (out / "hub_candidate.jsonl").open("w", encoding="utf-8") as fh:
                for h in hubs:
                    fh.write(json.dumps(h, ensure_ascii=False) + "\n")
            (out / "hub_build_report.md").write_text(bh.build_report(hubs, mem, stats, thr), encoding="utf-8")

    qf_label = " [--quality-filter]" if qf else ""
    print(f"=== しきい値比較 (有斐閣 + 学陽){qf_label} ===")
    if qf:
        print(f"{'thr':>4} {'hubs':>9} {'exact統合':>10} {'辞書またぎ':>11} {'読み救済':>10} {'homograph':>11} {'空def要前処理':>14} {'短def要前処理':>14}")
        for thr, st, xd in rows:
            print(f"{thr:>4} {st['hubs']:>9} {st['exact_merged_hubs']:>10} {xd:>11} "
                  f"{st.get('reading_missing_matched', 0):>10} {st['homograph_conflicts']:>11} "
                  f"{st.get('anchors_empty_def', 0):>14} {st.get('anchors_short_def', 0):>14}")
    else:
        print(f"{'thr':>4} {'hubs':>9} {'exact統合':>10} {'辞書またぎ':>11} {'読み救済':>10} {'homograph':>11}")
        for thr, st, xd in rows:
            print(f"{thr:>4} {st['hubs']:>9} {st['exact_merged_hubs']:>10} {xd:>11} "
                  f"{st.get('reading_missing_matched', 0):>10} {st['homograph_conflicts']:>11}")
    print(f"\n[run_2dict] report(0.6) -> {out}/hub_build_report.md")
    print("[run_2dict] 「辞書またぎ」= 有斐閣と学陽が同一 hub に統合された数 / homograph = 同見出し+読みで定義が食い違い別hubにした数")
    if qf:
        print("[run_2dict] 「空def/短def要前処理」= anchor が空定義/短定義の hub 数 (needs_preprocessing フラグ付き)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
