#!/usr/bin/env python3
"""articles_extracted.jsonl から条文・判例参照を抽出し e-gov へリンクする (Fork 4 ③).

Usage:
    python scripts/run_legal_links.py \
        --articles <articles_extracted.jsonl> \
        --egov data/egov/egov_statutory_definitions_ALL.jsonl \
        --out <out-dir>

出力:
  - legal_links.jsonl        … 1 行 1 link record (statute_ref / case_citation)
  - legal_links_summary.csv  … journal 別の参照件数集計
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.egov_index import EgovIndex  # noqa: E402
from codex.legal_links import link_article_row  # noqa: E402


def run(articles_path: str, egov_path: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    index = EgovIndex.load(egov_path)

    links: list[dict] = []
    with open(articles_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            links.extend(link_article_row(row, index))

    # 冪等な順序
    links.sort(key=lambda r: (r.get("journal_book_id") or "", r.get("ordinal") or 0,
                              r.get("char_start") or 0, r.get("scheme") or ""))

    links_path = os.path.join(out_dir, "legal_links.jsonl")
    with open(links_path, "w", encoding="utf-8") as f:
        for r in links:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # journal 別集計
    per_book = {}
    for r in links:
        b = r.get("journal_book_id") or ""
        d = per_book.setdefault(b, Counter())
        d[r["scheme"]] += 1
        if r["scheme"] == "jp_statute_ref":
            if r.get("article"):
                d["statute_ref_with_article"] += 1
            if r.get("article_in_egov"):
                d["statute_ref_egov_confirmed"] += 1
            d["conf_" + (r.get("confidence") or "na")] += 1

    summary_path = os.path.join(out_dir, "legal_links_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["journal_book_id", "statute_ref", "statute_ref_with_article",
                    "statute_ref_egov_confirmed", "statute_conf_high",
                    "statute_conf_medium", "statute_conf_low", "case_citation"])
        for b in sorted(per_book):
            d = per_book[b]
            w.writerow([b, d["jp_statute_ref"], d["statute_ref_with_article"],
                        d["statute_ref_egov_confirmed"], d["conf_high"],
                        d["conf_medium"], d["conf_low"], d["jp_case_citation"]])

    n_statute = sum(1 for r in links if r["scheme"] == "jp_statute_ref")
    n_case = sum(1 for r in links if r["scheme"] == "jp_case_citation")
    n_egov = sum(1 for r in links if r.get("article_in_egov"))
    n_high = sum(1 for r in links if r.get("confidence") == "high")
    return {
        "total_links": len(links),
        "statute_refs": n_statute,
        "statute_refs_high_conf": n_high,
        "case_citations": n_case,
        "egov_confirmed_articles": n_egov,
        "laws_indexed": len(index.name_to_law),
        "links_path": links_path,
        "summary_path": summary_path,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--articles", required=True)
    ap.add_argument("--egov", default=os.path.join(
        os.path.dirname(__file__), "..", "data", "egov",
        "egov_statutory_definitions_ALL.jsonl"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    stats = run(args.articles, args.egov, args.out)
    print(f"laws indexed          : {stats['laws_indexed']}")
    print(f"total links            : {stats['total_links']}")
    print(f"  statute refs         : {stats['statute_refs']} (high-conf {stats['statute_refs_high_conf']})")
    print(f"  (egov-confirmed art) : {stats['egov_confirmed_articles']}")
    print(f"  case citations       : {stats['case_citations']}")
    print(f"links  : {stats['links_path']}")
    print(f"summary: {stats['summary_path']}")


if __name__ == "__main__":
    main()
