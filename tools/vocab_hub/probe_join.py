#!/usr/bin/env python3
"""診断: 有斐閣×学陽 の cross-dict 一致を「読みあり/なし」で内訳する.

run_2dict.py の結果(辞書またぎ=0)の原因が「読みの欠落で同キーにならない」かどうかを実測.
read-only. 出力は標準出力(数字のみ).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import adapt_hourei as ah
import build_hub_dryrun as bh

CANDIDATE_ROOTS = ["Library/CloudStorage", "Box"]


def find_one(name, override=None):
    if override:
        return Path(override)
    for root in CANDIDATE_ROOTS:
        base = Path.home() / root
        if base.exists():
            for p in base.rglob(name):
                return p
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yt", default=None)
    ap.add_argument("--he", default=None)
    a = ap.parse_args(argv)
    yt = find_one("yuhikaku_legal_dict_terms_stg_v3.jsonl", a.yt)
    he = find_one("hourei_all_entries_v0.2_20260612.jsonl", a.he)
    print(f"[probe] yuhikaku: {yt}")
    print(f"[probe] hourei  : {he}")
    if not (yt and he):
        return 2

    # 有斐閣
    y_terms = list(bh.read_jsonl(yt))
    y_with_reading = sum(1 for t in y_terms if t.get("reading"))
    y_keys_pref = {}     # norm_pref -> set of (norm_pref, reading)
    y_keys_full = set()  # (norm_pref, norm_reading)
    for t in y_terms:
        p = bh.norm_pref(t.get("normalized_pref") or t.get("pref_label") or "")
        r = bh.norm_reading(t.get("reading", ""))
        if not p:
            continue
        y_keys_pref.setdefault(p, set()).add(r)
        y_keys_full.add((p, r))

    # 学陽 (adapt)
    h_entries = [json.loads(x) for x in he.read_text(encoding="utf-8").splitlines() if x.strip()]
    h_terms = ah.adapt(h_entries, "hourei", 102)
    h_with_reading = sum(1 for t in h_terms if t.get("reading"))
    h_pref_keys = []
    h_full_keys = []
    for t in h_terms:
        p = bh.norm_pref(t.get("normalized_pref") or t.get("pref_label") or t.get("headword") or "")
        r = bh.norm_reading(t.get("reading", ""))
        if not p:
            continue
        h_pref_keys.append(p)
        h_full_keys.append((p, r))

    full_hit = sum(1 for k in h_full_keys if k in y_keys_full)
    pref_hit = sum(1 for p in h_pref_keys if p in y_keys_pref)
    # 学陽側は読みあり/なしで内訳
    h_no_reading = [(p, r) for p, r in h_full_keys if not r]
    h_with_reading_keys = [(p, r) for p, r in h_full_keys if r]
    full_hit_when_read = sum(1 for k in h_with_reading_keys if k in y_keys_full)
    pref_hit_when_noread = sum(1 for p, r in h_no_reading if p in y_keys_pref)
    # 学陽に読みあり かつ 有斐閣にも同 pref+reading が存在しないが pref は存在 (=読み違いで漏れた)
    leak_due_to_reading = sum(
        1 for p, r in h_with_reading_keys
        if (p, r) not in y_keys_full and p in y_keys_pref
    )

    print("\n=== 入力件数 ===")
    print(f"有斐閣 terms : {len(y_terms):>6}  (読みあり {y_with_reading}, distinct (pref,read) {len(y_keys_full)})")
    print(f"学陽   terms : {len(h_terms):>6}  (読みあり {h_with_reading}, 読みなし {len(h_terms) - h_with_reading})")

    print("\n=== cross-dict 一致内訳 ===")
    print(f"(pref+reading) 完全一致   : {full_hit:>6}   ← 現行ツールが見つけた数 (run_2dict の辞書またぎ候補 = 49 ≈ これ)")
    print(f"(pref のみ) 一致(上限)    : {pref_hit:>6}   ← STATUS の「2,100一致(78.9%)」に近いはず")
    print(f"  内訳: 学陽に読みあり 一致      : {full_hit_when_read}")
    print(f"        学陽に読みなし→pref一致 : {pref_hit_when_noread}")
    print(f"        読み不一致で漏れた数    : {leak_due_to_reading}  ← (pref一致 - 完全一致 - 読みなしfallback)")

    print("\n=== 解釈 ===")
    if full_hit < pref_hit * 0.5:
        print("→ (pref+reading) 厳密キーで「漏れ」が支配的. 読み欠落時の pref-only fallback を導入すべき.")
    else:
        print("→ (pref+reading) で大半を捉えている. 漏れは少なめ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
