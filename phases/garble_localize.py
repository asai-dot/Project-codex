#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
garble_localize.py — OCR化け見出し語の局在（3点測量の核）

near-miss（見出し語 ed<=1）だけでは別語と化けを分離できない（survey §4）。
そこで **定義文の高類似** をゲートに足す: 学陽の見出し語 X が 有斐閣の見出し語 Y と
ed<=1 で、かつ 学陽定義(X) と 有斐閣定義(Y) が高類似なら、X は Y のOCR化けの強い候補。

- 完全一致見出し（X==Y が両辞書にある）は除外（化けでなく一致）。
- 出力は**候補**であり自動修正しない（辞書間で定義語り口は異なるため閾値判定）。

入力:
  --gakuyo  学陽 all_entries.jsonl（headword, definition）
  --yuhikaku 有斐閣 all_entries（.jsonl/.txt; headword, definition）
  --min-len 見出し語最小長（既定3。短語の偶発ed1を抑制）
  --def-threshold 定義類似の閾値（SequenceMatcher ratio, 既定0.6）
出力: --out jsonl（gakuyo_term, yuhikaku_term, ed_kind, def_sim, gakuyo_def, yuhikaku_def）
"""
import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher


def nfkc(s):
    return unicodedata.normalize("NFKC", (s or "").strip())


def norm_def(s):
    # 定義比較用の正規化: NFKC + 空白/句読点ゆれを圧縮（OCRの細差に頑健化）
    s = nfkc(s)
    s = re.sub(r"[\s　,，、.．。;；:：]+", "", s)
    return s


def load_entries(path):
    """headword -> definition（最初の定義を採用）。jsonl/txt(jsonl) 両対応。"""
    hw2def = {}
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln or ln[0] != "{":
                continue
            try:
                o = json.loads(ln)
            except json.JSONDecodeError:
                continue
            hw = nfkc(o.get("headword") or o.get("term") or "")
            if not hw:
                continue
            hw2def.setdefault(hw, o.get("definition") or "")
    return hw2def


def deletes1(s):
    yield s
    for i in range(len(s)):
        yield s[:i] + s[i + 1:]


def build_delete_index(terms):
    idx = {}
    for t in terms:
        for d in deletes1(t):
            idx.setdefault(d, set()).add(t)
    return idx


def main(argv=None):
    ap = argparse.ArgumentParser(description="OCR化け見出し語の局在（定義一致ゲート）")
    ap.add_argument("--gakuyo", required=True)
    ap.add_argument("--yuhikaku", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-len", type=int, default=3)
    ap.add_argument("--def-threshold", type=float, default=0.6)
    args = ap.parse_args(argv)

    G = load_entries(args.gakuyo)
    Y = load_entries(args.yuhikaku)
    yset = set(Y)
    yidx = build_delete_index(yset)

    cands = []
    for gx, gdef in G.items():
        if len(gx) < args.min_len:
            continue
        if gx in yset:
            continue  # 完全一致＝化けでない
        if not gdef:
            continue
        cand_y = set()
        for d in deletes1(gx):
            cand_y |= yidx.get(d, set())
        gdn = norm_def(gdef)
        if not gdn:
            continue
        best = None
        for hy in cand_y:
            if hy == gx:
                continue
            ydn = norm_def(Y.get(hy, ""))
            if not ydn:
                continue
            sim = SequenceMatcher(None, gdn, ydn).ratio()
            if best is None or sim > best[1]:
                best = (hy, sim)
        if best and best[1] >= args.def_threshold:
            hy, sim = best
            kind = "same_len_sub" if len(gx) == len(hy) else "indel"
            cands.append({
                "gakuyo_term": gx, "yuhikaku_term": hy,
                "ed_kind": kind, "def_sim": round(sim, 3),
                "gakuyo_def": gdef[:120], "yuhikaku_def": Y.get(hy, "")[:120],
            })

    cands.sort(key=lambda c: -c["def_sim"])
    with open(args.out, "w", encoding="utf-8") as out:
        for c in cands:
            out.write(json.dumps(c, ensure_ascii=False) + "\n")

    print("=== garble_localize ===", file=sys.stderr)
    print(f"gakuyo entries     : {len(G)}", file=sys.stderr)
    print(f"yuhikaku entries   : {len(Y)}", file=sys.stderr)
    print(f"garble candidates  : {len(cands)}  (ed<=1 AND def_sim>={args.def_threshold})", file=sys.stderr)
    print(f"--- top 20 (highest def similarity) ---", file=sys.stderr)
    for c in cands[:20]:
        print(f"  [学陽]{c['gakuyo_term']} ~ [有斐閣]{c['yuhikaku_term']}  "
              f"sim={c['def_sim']} ({c['ed_kind']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
