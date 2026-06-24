#!/usr/bin/env python3
"""schema_probe: 実データ JSONL のフィールドを点検し field-map 雛形を出す (read-only).

実データのフィールド名が silver ツールの期待スキーマと違うかを確認し、
--field-map に渡す写像 JSON の雛形を生成する。手書き変換スクリプトを不要にする補助。

使い方:
  python3 tools/silver_resolve/schema_probe.py --jsonl <file> --expect lic|pub|canon|toc_nodes|toc_edges|hyoshaku
出力: フィールド一覧・充填率・期待キーの充足/欠落・field-map 雛形 (欠落キーのみ)。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional

EXPECTED = {
    "lic": ["edge_id", "edge_type", "source_locator", "court", "date"],
    "pub": ["hanrei_id", "journal", "issue", "page"],
    "canon": ["hanrei_id", "court", "date"],
    "toc_nodes": ["toc_node_id", "parent_id", "book_id", "heading", "kind"],
    "toc_edges": ["toc_node_id", "hanrei_id", "book_id"],
    "hyoshaku": ["hanrei_id", "hyoshaku_count"],
}


def probe(path: Path, expect_key: Optional[str], sample: int) -> str:
    n = 0
    fill = Counter()
    seen = set()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            n += 1
            for k, v in r.items():
                seen.add(k)
                if v not in (None, "", []):
                    fill[k] += 1
            if n >= sample:
                break
    lines = [f"# schema probe: {path.name}", "", f"- 標本行数: {n}", "", "## フィールド充填率",
             "| field | fill | fill% |", "|---|---|---|"]
    for k in sorted(seen):
        lines.append(f"| {k} | {fill[k]} | {fill[k] / n * 100:.0f}% |")

    if expect_key:
        exp = EXPECTED[expect_key]
        present = [k for k in exp if k in seen]
        missing = [k for k in exp if k not in seen]
        lines += ["", f"## 期待スキーマ ({expect_key})",
                  f"- 充足: {', '.join(present) or '(なし)'}",
                  f"- 欠落: {', '.join(missing) or '(なし)'}"]
        if missing:
            template = {m: "<actual_field_for_%s>" % m for m in missing}
            lines += ["", "## field-map 雛形 (欠落キーを実フィールドへ写像)",
                      "```json", json.dumps(template, ensure_ascii=False, indent=2), "```",
                      "→ 実フィールド名を埋めて `--field-map` に渡す。"]
        else:
            lines += ["", "期待キーは全て充足。--field-map 不要。"]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="silver 入力 JSONL のスキーマ点検 (read-only)")
    ap.add_argument("--jsonl", required=True, type=Path)
    ap.add_argument("--expect", choices=sorted(EXPECTED), default=None)
    ap.add_argument("--sample", type=int, default=2000)
    args = ap.parse_args(argv)
    print(probe(args.jsonl, args.expect, args.sample))
    return 0


if __name__ == "__main__":
    sys.exit(main())
