#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
triangulate_terms.py — 法律用語の3点測量（JLT × 学陽OCR × 三省堂…）

複数の見出し語リスト（ソース）を突き合わせ、(1) 各語の在/不在マトリクス集計、
(2) ソース間 edit-distance<=1 の近接ミス（OCR化け・表記ゆれ候補）を検出する。

近接検出は SymSpell 式 delete-1 索引で高速化（substitution/insertion/deletion を被覆）。
2点でも有効（学陽onlyの語が JLT権威語と1字違い → 学陽側OCR化けの強い候補）。
3点揃えば「2ソースで一致・1ソースで1字違い」= 高確度の誤り局在になる。

入力: --source LABEL=path（1行1語 txt、または jsonl で term/headword フィールド）を複数。
出力(stderr): 各ソース語数 / 在不在の組合せ集計 / 近接ペア件数。
      --pairs-out: 近接ペアを jsonl（label_a, term_a, label_b, term_b, kind）で書き出し。
"""
import argparse
import json
import sys
import unicodedata


def nfc(s):
    return unicodedata.normalize("NFC", (s or "").strip())


def load_terms(path):
    terms = set()
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            if ln[0] in "{[":
                try:
                    o = json.loads(ln)
                    t = o.get("term") or o.get("headword") or ""
                except json.JSONDecodeError:
                    t = ln
            else:
                t = ln
            t = nfc(t)
            if t:
                terms.add(t)
    return terms


def deletes1(s):
    """edit-distance<=1 被覆用: s 自身 + 1文字削除した全variant。"""
    yield s
    for i in range(len(s)):
        yield s[:i] + s[i + 1:]


def build_delete_index(terms):
    idx = {}
    for t in terms:
        for d in deletes1(t):
            idx.setdefault(d, set()).add(t)
    return idx


def near_misses(terms_a, idx_b, terms_b):
    """terms_a の各語について、terms_b 内で ed<=1 だが exact 不一致の相手を返す。"""
    out = []
    for a in terms_a:
        if a in terms_b:
            continue  # exact 一致は近接ではなく一致
        cand = set()
        for d in deletes1(a):
            cand |= idx_b.get(d, set())
        for b in cand:
            if b == a:
                continue
            kind = "same_len_sub" if len(a) == len(b) else "indel"
            out.append((a, b, kind))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="法律用語の3点測量")
    ap.add_argument("--source", action="append", required=True,
                    metavar="LABEL=PATH", help="LABEL=path を複数指定")
    ap.add_argument("--pairs-out")
    ap.add_argument("--min-len", type=int, default=3,
                    help="近接ミスの最小文字長（短語の偶発ed1を抑制。既定3）")
    ap.add_argument("--unique-only", action="store_true",
                    help="近接ミスの起点を『1ソースのみに在る語』に限定（OCR化け炙り出し）")
    args = ap.parse_args(argv)

    sources = {}
    for spec in args.source:
        if "=" not in spec:
            print(f"bad --source (need LABEL=PATH): {spec}", file=sys.stderr)
            return 2
        label, path = spec.split("=", 1)
        sources[label] = load_terms(path)

    labels = list(sources)
    union = set().union(*sources.values()) if sources else set()

    print("=== triangulate_terms ===", file=sys.stderr)
    for lb in labels:
        print(f"  {lb:12s}: {len(sources[lb])} terms", file=sys.stderr)
    print(f"  union       : {len(union)}", file=sys.stderr)

    # 在不在の組合せ集計
    from collections import Counter
    combo = Counter()
    for t in union:
        key = tuple(lb for lb in labels if t in sources[lb])
        combo[key] += 1
    print("--- presence combinations ---", file=sys.stderr)
    for key, n in sorted(combo.items(), key=lambda kv: -kv[1]):
        print(f"  {'+'.join(key) or '(none)'}: {n}", file=sys.stderr)

    # 起点語の選定: --unique-only なら「1ソースのみに在る語」に限定（OCR化け候補）。
    presence = {t: [lb for lb in labels if t in sources[lb]] for t in union}
    def probe_set(la):
        base = sources[la]
        if args.unique_only:
            base = {t for t in base if len(presence[t]) == 1}
        return {t for t in base if len(t) >= args.min_len}

    # 近接ミス（全ソースペア、片方向: a を相手の索引に当てる）
    pairs = []
    for la in labels:
        probe = probe_set(la)
        for lb in labels:
            if la == lb:
                continue
            idx_b = build_delete_index(sources[lb])
            for a, b, kind in near_misses(probe, idx_b, sources[lb]):
                pairs.append({"label_a": la, "term_a": a,
                              "label_b": lb, "term_b": b, "kind": kind})
    # 重複（a→b と b→a）を片側化: (min,max) で一意化
    seen = set()
    uniq_pairs = []
    for p in pairs:
        k = tuple(sorted([(p["label_a"], p["term_a"]), (p["label_b"], p["term_b"])]))
        if k in seen:
            continue
        seen.add(k)
        uniq_pairs.append(p)

    print(f"--- near-miss (ed<=1, exact不一致) : {len(uniq_pairs)} pairs ---", file=sys.stderr)
    for p in uniq_pairs[:15]:
        print(f"  [{p['label_a']}]{p['term_a']}  ~  [{p['label_b']}]{p['term_b']}  ({p['kind']})",
              file=sys.stderr)

    if args.pairs_out:
        with open(args.pairs_out, "w", encoding="utf-8") as out:
            for p in uniq_pairs:
                out.write(json.dumps(p, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
