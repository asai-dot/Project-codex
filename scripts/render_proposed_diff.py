"""overwrites_bundle.jsonl → 人間可読の旧/新 TOC 差分 markdown.

Mac セッションのドライランが吐いた `overwrites_bundle.jsonl` を本リポジトリへ
戻し、こちら側で overwrite_simple 候補を 1 件ずつ目視レビューするためのツール。
books.json も legallib_dir も不要 (バンドルだけで完結)。

各 ISBN について:
  * 旧 (simple) と 新 (legallib) のノード数。
  * 追加されたタイトル / 消えたタイトル (正規化タイトルの集合差)。
  * 判定: ``enrich`` (新が旧を包含し増加 = 安全な高精度化) /
    ``replace`` (旧の一部が新に無い = 中身が入れ替わる、要確認)。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import title_set  # noqa: E402


def _iter_bundle(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def classify(existing: list[dict], new: list[dict]) -> dict:
    old_t = title_set(existing)
    new_t = title_set(new)
    removed = old_t - new_t      # 旧にあって新に無い = 失われるタイトル
    added = new_t - old_t
    kind = "enrich" if not removed and len(new) >= len(existing) else "replace"
    return {
        "old_nodes": len(existing),
        "new_nodes": len(new),
        "added": len(added),
        "removed_titles": sorted(removed),
        "kind": kind,
    }


def render(bundle_path: Path, limit: int | None = None) -> str:
    rows = list(_iter_bundle(bundle_path))
    # ヘッダ集計は per-row の classify と同じ基準を使う (表示と矛盾させない)。
    enrich = sum(1 for r in rows
                 if classify(r["existing_nodes"], r["new_nodes"])["kind"] == "enrich")
    out = [
        "# legallib overwrite_simple 差分レビュー",
        "",
        f"- 対象 (simple→legallib 上書き候補): {len(rows)} 件",
        f"- うち enrich (旧を包含・安全): {enrich} 件 / replace (要確認): {len(rows) - enrich} 件",
        "",
    ]
    shown = rows if limit is None else rows[:limit]
    for r in shown:
        c = classify(r["existing_nodes"], r["new_nodes"])
        flag = "✅ enrich" if c["kind"] == "enrich" else "⚠ replace"
        out.append(f"## {r['isbn']}  ({flag})  旧{c['old_nodes']}→新{c['new_nodes']} (+{c['added']})")
        if c["removed_titles"]:
            out.append("")
            out.append(f"  失われるタイトル {len(c['removed_titles'])} 件:")
            for t in c["removed_titles"][:10]:
                out.append(f"  - {t}")
        out.append("")
    if limit is not None and len(rows) > limit:
        out.append(f"... 他 {len(rows) - limit} 件 (--limit 省略で全件)")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="overwrite 差分レビュー markdown 生成")
    ap.add_argument("--bundle", required=True, help="overwrites_bundle.jsonl")
    ap.add_argument("--out", help="出力 md (省略時 stdout)")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)

    md = render(Path(args.bundle), args.limit)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
