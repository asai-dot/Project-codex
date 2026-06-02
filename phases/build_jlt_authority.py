#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_jlt_authority.py — 法務省 JLT v19.0「法令用語日英標準対訳辞書」CSV から
権威ある見出し語リストを決定的に生成する。

入力: jlt_dict_v19.0_utf8.csv（ヘッダ: 用語,読み,訳語候補番号,訳語候補,使い分け基準,
      用例(和文),用例(英文),用例出典,注釈1,注釈2）。用語ごとに訳語候補で複数行。
出力:
  - <out_terms>      : 一意な見出し語（NFC・ソート）を1行1語。← 2辞書突合の権威基準
  - <pairs_out>(任意): (用語, 読み) 一意ペアの jsonl
報告(stderr): 行数 / 一意用語数 / 一意(用語,読み)数 / term-set sha256（再現性・正典再抽出と照合用）。

権威性: 入力は byte-exact 正典（sha256 を別途確認のこと）。本スクリプトは生データを改変しない。

使い方:
  python3 build_jlt_authority.py jlt_dict_v19.0_utf8.csv jlt_terms_authority.txt \
          [--term-col 用語] [--reading-col 読み] [--pairs-out jlt_term_reading.jsonl]
"""
import argparse
import csv
import hashlib
import json
import sys
import unicodedata


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").strip())


def main(argv=None):
    ap = argparse.ArgumentParser(description="JLT v19.0 CSV -> 権威見出し語リスト")
    ap.add_argument("csv_path")
    ap.add_argument("out_terms")
    ap.add_argument("--term-col", default="用語")
    ap.add_argument("--reading-col", default="読み")
    ap.add_argument("--encoding", default="utf-8-sig")  # BOM 許容
    ap.add_argument("--pairs-out")
    args = ap.parse_args(argv)

    rows = 0
    terms = set()
    pairs = set()
    with open(args.csv_path, encoding=args.encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        if args.term_col not in (reader.fieldnames or []):
            print(f"term-col '{args.term_col}' not in header: {reader.fieldnames}",
                  file=sys.stderr)
            return 2
        for row in reader:
            rows += 1
            t = nfc(row.get(args.term_col, ""))
            if not t:
                continue
            terms.add(t)
            pairs.add((t, nfc(row.get(args.reading_col, ""))))

    sorted_terms = sorted(terms)
    body = "\n".join(sorted_terms)
    with open(args.out_terms, "w", encoding="utf-8") as out:
        out.write(body + ("\n" if body else ""))

    if args.pairs_out:
        with open(args.pairs_out, "w", encoding="utf-8") as pf:
            for t, r in sorted(pairs):
                pf.write(json.dumps({"term": t, "reading": r}, ensure_ascii=False) + "\n")

    term_set_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    print("=== build_jlt_authority report ===", file=sys.stderr)
    print(f"data rows           : {rows}", file=sys.stderr)
    print(f"unique terms        : {len(terms)}", file=sys.stderr)
    print(f"unique term+reading : {len(pairs)}", file=sys.stderr)
    print(f"term-set sha256     : {term_set_sha256}", file=sys.stderr)
    print(f"out_terms           : {args.out_terms}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
