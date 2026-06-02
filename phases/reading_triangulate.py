#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reading_triangulate.py — 読み（ふりがな）の三点測量で OCRミスを炙り出す

同一見出し語が複数辞書にあるとき、読みは一致するはず。食い違えば OCRミスの疑い。
特に JLT（法務省・権威読み100%）を基準にすると、有斐閣・学陽側の読み化けが出る。
食い違いの「型」を分類して、真のOCRミス（濁点落ち・小書き・欠落）と
正当な異読/抽出truncation を切り分ける。生データ非改変・suspect は別レイヤ。

入力: --source LABEL=path（jsonl: term/headword + reading、or jlt の term_reading.jsonl）
      --authority LABEL（基準ソース。既定 JLT）
出力: --out jsonl（headword, authority_reading, other_label, other_reading, diff_type, likely_wrong）
"""
import argparse
import json
import sys
import unicodedata

DAKU = str.maketrans(
    "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ",
    "かきくけこさしすせそたちつてとはひふへほはひふへほ")
SMALL = str.maketrans("ぁぃぅぇぉっゃゅょゎ", "あいうえおつやゆよわ")


def nf(s):
    return unicodedata.normalize("NFKC", (s or "").strip()).replace("・", "").replace(" ", "")


def load(path):
    d = {}
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if ln[:1] != "{":
            continue
        o = json.loads(ln)
        hw = nf(o.get("headword") or o.get("term") or "")
        r = nf(o.get("reading", ""))
        if hw and r:
            d.setdefault(hw, r)
    return d


def classify(a, b):
    """a=権威読み, b=他ソース読み。差の型を返す。"""
    if a == b:
        return "same"
    if b and (b in a or a in b):
        return "truncation_or_partial"   # 片方が他方の部分（抽出truncation/欠落）
    if a.translate(DAKU) == b.translate(DAKU):
        return "dakuten"                  # 濁点/半濁点のみ差
    if a.translate(SMALL) == b.translate(SMALL):
        return "small_kana"               # っ/ゃゅょ 等の小書き差
    if a.translate(DAKU).translate(SMALL) == b.translate(DAKU).translate(SMALL):
        return "dakuten+small"
    if abs(len(a) - len(b)) >= 1:
        return "len_diff"                 # 文字数差（挿入/欠落）
    return "substitution"                 # 同長置換


def main(argv=None):
    ap = argparse.ArgumentParser(description="読みの三点測量（OCRミス炙り出し）")
    ap.add_argument("--source", action="append", required=True, metavar="LABEL=PATH")
    ap.add_argument("--authority", default="JLT")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    src = {}
    for spec in args.source:
        lb, p = spec.split("=", 1)
        src[lb] = load(p)
    auth = args.authority
    if auth not in src:
        print(f"authority '{auth}' not among sources {list(src)}", file=sys.stderr)
        return 2

    A = src[auth]
    rows = []
    for lb, d in src.items():
        if lb == auth:
            continue
        shared = A.keys() & d.keys()
        for hw in shared:
            t = classify(A[hw], d[hw])
            if t == "same":
                continue
            # likely_wrong: truncation/部分なら他ソース、それ以外も権威基準で他ソースが疑わしい
            rows.append({"headword": hw, "authority": auth, "authority_reading": A[hw],
                         "other_label": lb, "other_reading": d[hw],
                         "diff_type": t, "likely_wrong": lb})

    from collections import Counter
    by_pair = Counter((r["other_label"]) for r in rows)
    by_type = Counter(r["diff_type"] for r in rows)
    rows.sort(key=lambda r: (r["other_label"], r["diff_type"], r["headword"]))
    with open(args.out, "w", encoding="utf-8") as out:
        for r in rows:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("=== reading_triangulate (authority=%s) ===" % auth, file=sys.stderr)
    for lb, d in src.items():
        if lb != auth:
            shared = len(A.keys() & d.keys())
            print(f"  {auth}∩{lb}: shared-w/-reading {shared}", file=sys.stderr)
    print(f"  total disagreements: {len(rows)}", file=sys.stderr)
    print("  by source:", dict(by_pair), file=sys.stderr)
    print("  by diff_type:", dict(by_type), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
