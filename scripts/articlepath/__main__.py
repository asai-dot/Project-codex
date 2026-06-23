"""CLI: normalize article paths from a lawdelta JSONL, and build a crosswalk.

    python -m scripts.articlepath --delta out/law_textual_delta_<run>.jsonl \
        --out out/articlepath_<run>

Emits:
  <out>_crosswalk.jsonl   old↔new mappings for changed articles
  <out>_report.json       canonicalization + a string-vs-numeric sort audit
                          (demonstrates why a numeric sort key is needed)
"""
from __future__ import annotations

import argparse
import json
import os
from typing import List

from .normalize import parse, ParseError
from .crosswalk import build_crosswalk, old_to_new_index


def _load(path: str) -> List[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scripts.articlepath")
    ap.add_argument("--delta", required=True, help="lawdelta JSONL (pred)")
    ap.add_argument("--out", required=True, help="output prefix")
    args = ap.parse_args(argv)

    rows = _load(args.delta)
    paths = [r["article_path"] for r in rows if r.get("article_path")]

    canon, unparseable = {}, []
    for p in paths:
        try:
            canon[p] = parse(p)
        except ParseError as e:
            unparseable.append({"path": p, "error": str(e)})

    # string sort vs numeric sort: where do they disagree?
    string_sorted = sorted(canon)
    numeric_sorted = sorted(canon, key=lambda p: canon[p].sort_key())
    disagreements = [
        {"position": i, "string_sort": s, "numeric_sort": n}
        for i, (s, n) in enumerate(zip(string_sorted, numeric_sorted)) if s != n
    ][:20]

    entries = build_crosswalk(rows)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(f"{args.out}_crosswalk.jsonl", "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")

    report = {
        "delta_path": args.delta,
        "articles_seen": len(paths),
        "canonicalized": len(canon),
        "unparseable": unparseable,
        "changed_articles": len(entries),
        "by_relation": _count(e.relation for e in entries),
        "string_vs_numeric_sort_disagreements": len(disagreements),
        "sort_disagreement_examples": disagreements,
        "crosswalk_old_to_new_sample": dict(list(old_to_new_index(entries).items())[:10]),
    }
    with open(f"{args.out}_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in
                      ("articles_seen", "canonicalized", "unparseable",
                       "changed_articles", "by_relation",
                       "string_vs_numeric_sort_disagreements")},
                     ensure_ascii=False, indent=2))
    return 0


def _count(it) -> dict:
    d: dict = {}
    for x in it:
        d[x] = d.get(x, 0) + 1
    return dict(sorted(d.items()))


if __name__ == "__main__":
    raise SystemExit(main())
