"""legallib_dl/*.json の preflight スキーマ点検 (Mac セッションが接合前に実行).

変換器 (`legallib_to_canonical.py`) の前提が実データと合っているかを、
ディレクトリをサンプリングして診断する。ハード失敗はせず、report を出す。

報告内容:
  * ファイル数 / book vs journal の内訳 (content_type)。
  * toc ノード列が入っている top-level key (toc / nodes / 直リスト 等)。
  * ノードの level 分布 (最小・最大・depth ヒストグラム)。
  * タイトルキー (t/title/label …) の出現頻度。
  * 空タイトル率 / ページ付与率。

変換器の想定 (level・t・page) と乖離があればここで判明し、Mac 着手前に
converter を調整できる。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from legallib_to_canonical import (  # noqa: E402
    _LEVEL_KEYS,
    _PAGE_KEYS,
    _TITLE_KEYS,
    _coerce_level,
    _coerce_page,
    _coerce_title,
)

_NODE_LIST_KEYS = ("toc", "nodes", "toc_nodes", "items")


def _node_list(data) -> tuple[str, list]:
    if isinstance(data, list):
        return "<root-list>", data
    if isinstance(data, dict):
        for k in _NODE_LIST_KEYS:
            if isinstance(data.get(k), list):
                return k, data[k]
    return "<none>", []


def inspect_dir(path: Path, sample: int | None = None) -> dict:
    files = sorted(path.glob("*.json"))
    if sample:
        files = files[:sample]

    content_types = Counter()
    list_keys = Counter()
    title_keys = Counter()
    level_keys = Counter()
    page_keys = Counter()
    levels = Counter()
    total_nodes = 0
    empty_titles = 0
    nodes_with_page = 0
    unreadable = 0

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            unreadable += 1
            continue
        if isinstance(data, dict):
            content_types[str(data.get("content_type") or "<unset>")] += 1
        lk, nodes = _node_list(data)
        list_keys[lk] += 1
        for n in nodes:
            if not isinstance(n, dict):
                continue
            total_nodes += 1
            for key in _TITLE_KEYS:
                if n.get(key) not in (None, ""):
                    title_keys[key] += 1
                    break
            for key in _LEVEL_KEYS:
                if n.get(key) not in (None, ""):
                    level_keys[key] += 1
                    break
            for key in _PAGE_KEYS:
                if n.get(key) not in (None, ""):
                    page_keys[key] += 1
                    break
            if not _coerce_title(n):
                empty_titles += 1
            levels[_coerce_level(n)] += 1
            if _coerce_page(n) is not None:
                nodes_with_page += 1

    return {
        "files": len(files),
        "unreadable": unreadable,
        "content_types": dict(content_types),
        "node_list_keys": dict(list_keys),
        "title_keys": dict(title_keys),
        "level_keys": dict(level_keys),
        "page_keys": dict(page_keys),
        "total_nodes": total_nodes,
        "level_histogram": dict(sorted(levels.items())),
        "empty_title_rate": round(empty_titles / total_nodes, 4) if total_nodes else None,
        "page_coverage": round(nodes_with_page / total_nodes, 4) if total_nodes else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="legallib_dl スキーマ点検")
    ap.add_argument("--legallib-dir", required=True)
    ap.add_argument("--sample", type=int, help="先頭 N 冊だけ点検")
    ap.add_argument("--json", action="store_true", help="JSON で出力")
    args = ap.parse_args(argv)

    res = inspect_dir(Path(args.legallib_dir), args.sample)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for k, v in res.items():
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
