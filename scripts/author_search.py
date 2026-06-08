#!/usr/bin/env python3
"""著者横断検索 (Fork 4 検収「著者横断検索が成立」).

articles_extracted.jsonl から正規化著者キーで逆引き索引を作り、著者名で
その著者の全論文 (雑誌横断) を引く。表記揺れ (全角空白/敬称/所属注記) は
author_normalize で吸収されるため、揺れた表記でもヒットする。

Usage:
    # 索引統計 + 多作著者ランキング
    python scripts/author_search.py --articles out/articles_extracted.jsonl --top 10

    # 特定著者を検索 (表記揺れ可)
    python scripts/author_search.py --articles out/articles_extracted.jsonl --query "山口 厚"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.author_normalize import normalize_author, author_keys  # noqa: E402


def build_index(articles_path: str):
    """author_key -> [ {journal_book_id, journal_title, ordinal, title, display} ]"""
    idx: dict[str, list[dict]] = defaultdict(list)
    display_for_key: dict[str, str] = {}
    with open(articles_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("kind") != "article" or not row.get("authors"):
                continue
            for a in row["authors"]:
                n = normalize_author(a)
                if not n["key"]:
                    continue
                display_for_key.setdefault(n["key"], n["display"])
                idx[n["key"]].append({
                    "journal_book_id": row["journal_book_id"],
                    "journal_title": row["journal_title"],
                    "ordinal": row["ordinal"],
                    "title": row["title"],
                    "display": n["display"],
                })
    return idx, display_for_key


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--articles", required=True)
    ap.add_argument("--query", help="検索する著者名 (表記揺れ可)")
    ap.add_argument("--top", type=int, default=10, help="多作著者ランキング件数")
    args = ap.parse_args()

    idx, display_for_key = build_index(args.articles)

    if args.query:
        keys = author_keys([args.query]) or [normalize_author(args.query)["key"]]
        key = keys[0] if keys else ""
        hits = idx.get(key, [])
        print(f'query "{args.query}" -> key "{key}" : {len(hits)} article(s)')
        for h in sorted(hits, key=lambda x: (x["journal_book_id"], x["ordinal"])):
            print(f'  [{h["journal_book_id"]} #{h["ordinal"]}] {h["display"]} — {h["title"]}')
            print(f'       in: {h["journal_title"]}')
        return

    # 索引統計
    n_authors = len(idx)
    n_pairs = sum(len(v) for v in idx.values())
    print(f"distinct authors (normalized): {n_authors}")
    print(f"author-article links         : {n_pairs}")
    cross = [(k, v) for k, v in idx.items()
             if len({x["journal_book_id"] for x in v}) >= 2]
    print(f"authors appearing in >=2 journals (cross-journal): {len(cross)}")
    print(f"\nTop {args.top} prolific authors:")
    for k, v in sorted(idx.items(), key=lambda kv: len(kv[1]), reverse=True)[:args.top]:
        books = len({x["journal_book_id"] for x in v})
        print(f"  {display_for_key[k]:<12} {len(v):3d} articles across {books} journal(s)")


if __name__ == "__main__":
    main()
