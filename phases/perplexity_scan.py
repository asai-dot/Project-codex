#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
perplexity_scan.py — C2: 文字N-gram surprisal で本文の「あり得ない並び」を炙り出す

ニューラルLMの代理として、清浄な法律日本語コーパス（e-Gov法令本文＋辞書定義）で学習した
**文字trigram言語モデル**を使う。OCR化け（誤字・mojibake・濁点ずれ）は学習コーパスで稀/未出の
3-gramを作り surprisal（-logP）が跳ねる。引用・並行権威に依存せず本文全面を掃ける。

- 学習: --corpus-def（jsonl, definition抽出）/ --corpus-raw（生テキスト, 日本語抽出）を複数。
- 採点: --score（jsonl, headword/definition）の各定義を1文字ずつ surprisal 採点。
  trigram→bigram→unigram の stupid-backoff。
- 出力: surprisal が高い連続スパン（CJK含む）を文脈付きで、降順。誤字脱字の候補。

自動修正しない・suspect層。上位を目視して実OCR化けか検証する用途。
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict, Counter

CJK = re.compile(r"[぀-ゟ゠-ヿ一-鿿々〆ヶ]")


def jp_only(s):
    # 採点対象は日本語本文。空白圧縮のみ（句読点は文脈として残す）。
    return s


def iter_corpus(args):
    for p in (args.corpus_def or []):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln[:1] == "{":
                try:
                    yield json.loads(ln).get("definition", "") or ""
                except json.JSONDecodeError:
                    pass
    for p in (args.corpus_raw or []):
        raw = open(p, encoding="utf-8").read()
        # e-Gov JSON 等から日本語文字列値を抽出
        for v in re.findall(r'"((?:[^"\\]|\\.)*)"', raw):
            if CJK.search(v):
                yield v


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", required=True)
    ap.add_argument("--corpus-def", action="append")
    ap.add_argument("--corpus-raw", action="append")
    ap.add_argument("--out", required=True)
    ap.add_argument("--topn", type=int, default=40)
    ap.add_argument("--thr", type=float, default=12.0, help="surprisal閾値(bits)")
    args = ap.parse_args(argv)

    tri = defaultdict(Counter)   # (a,b)->c
    bi = defaultdict(Counter)    # a->b
    uni = Counter()
    n = 0
    for text in iter_corpus(args):
        s = "\x02\x02" + text + "\x03"
        for i, c in enumerate(s):
            uni[c] += 1
            n += 1
            if i >= 1:
                bi[s[i - 1]][c] += 1
            if i >= 2:
                tri[(s[i - 2], s[i - 1])][c] += 1
    V = len(uni)
    LAMBDA = 0.4

    def logp(a, b, c):
        t = tri.get((a, b))
        if t and t[c] > 0:
            return math.log2(t[c] / sum(t.values()))
        bb = bi.get(b)
        if bb and bb[c] > 0:
            return math.log2(LAMBDA * bb[c] / sum(bb.values()))
        # unigram backoff (add-1)
        return math.log2((LAMBDA * LAMBDA) * (uni[c] + 1) / (n + V))

    suspects = []
    for ln in open(args.score, encoding="utf-8"):
        o = json.loads(ln)
        d = o.get("definition", "") or ""
        s = "\x02\x02" + d + "\x03"
        surp = [(-logp(s[i - 2], s[i - 1], s[i])) for i in range(2, len(s))]
        # 高surprisalの連続スパンをまとめる
        i = 0
        chars = s[2:]
        while i < len(chars):
            if surp[i] >= args.thr and CJK.search(chars[i] or " "):
                j = i
                while j < len(chars) and surp[j] >= args.thr - 3:
                    j += 1
                span = chars[i:j]
                ctx = d[max(0, i - 8):j + 8]
                suspects.append({"headword": o.get("headword"), "span": span,
                                 "max_surprisal": round(max(surp[i:j]), 1),
                                 "context": ctx})
                i = j
            else:
                i += 1

    suspects.sort(key=lambda x: -x["max_surprisal"])
    with open(args.out, "w", encoding="utf-8") as out:
        for s in suspects:
            out.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"=== perplexity_scan ===", file=sys.stderr)
    print(f"corpus chars: {n}  vocab: {V}", file=sys.stderr)
    print(f"suspect spans (surprisal>={args.thr}): {len(suspects)}", file=sys.stderr)
    print(f"--- top {args.topn} (highest surprisal) ---", file=sys.stderr)
    for s in suspects[:args.topn]:
        print(f"  [{s['max_surprisal']}] 「{s['span']}」 …{s['context']}… ({s['headword']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
