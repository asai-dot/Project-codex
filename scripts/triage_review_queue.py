"""review_bundle.jsonl → 保護衝突レビューのトリアージ.

Mac セッションのドライランが吐いた `review_bundle.jsonl` (legallib auto_accept が
人手/NDL/出版社/PDF目次の既存と衝突し route_human_review になったもの) を
本リポジトリへ戻し、こちら側で人が裁定しやすい順に並べる。

各 ISBN について既存タイトル集合と legallib 候補タイトル集合の重なり (Jaccard) を
計算し分類:
  * ``candidate_richer`` : 候補が既存を概ね包含し、ノード数も増える
    → legallib 階層で人手版を「補強」できる可能性 (人が確認の上 merge 検討)。
  * ``near_duplicate``   : 重なり大・件数同程度 → 既存維持でよい公算大 (低優先)。
  * ``conflict``         : 重なり小 → 別物の疑い (resolver 突合を疑う、高優先)。

出力は CSV (機械処理用) と markdown サマリ。**書き込みは一切しない**。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import jaccard, title_set  # noqa: E402


def _iter_bundle(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def classify(existing: list[dict], candidate: list[dict]) -> dict:
    old_t = title_set(existing)
    new_t = title_set(candidate)
    j = jaccard(old_t, new_t)
    contained = (len(old_t & new_t) / len(old_t)) if old_t else 0.0  # 既存の何割が候補に在るか
    if contained >= 0.8 and len(candidate) > len(existing):
        kind = "candidate_richer"
    elif j >= 0.6:
        kind = "near_duplicate"
    else:
        kind = "conflict"
    return {
        "jaccard": round(j, 3),
        "existing_coverage": round(contained, 3),
        "old_nodes": len(existing),
        "cand_nodes": len(candidate),
        "kind": kind,
    }


# 優先度: conflict (突合疑い) を最優先、次に richer、最後に near_duplicate。
_PRIORITY = {"conflict": 0, "candidate_richer": 1, "near_duplicate": 2}


def triage(bundle_path: Path) -> list[dict]:
    rows = []
    for r in _iter_bundle(bundle_path):
        c = classify(r["existing_nodes"], r["candidate_nodes"])
        rows.append({
            "isbn": r["isbn"],
            "book_id": r.get("book_id", ""),
            "existing_primary_source": r.get("existing_primary_source", ""),
            **c,
        })
    rows.sort(key=lambda x: (_PRIORITY[x["kind"]], -x["cand_nodes"]))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="review_bundle トリアージ")
    ap.add_argument("--bundle", required=True, help="review_bundle.jsonl")
    ap.add_argument("--out-csv")
    ap.add_argument("--out-md")
    args = ap.parse_args(argv)

    rows = triage(Path(args.bundle))
    kinds = Counter(r["kind"] for r in rows)
    srcs = Counter(r["existing_primary_source"] for r in rows)

    if args.out_csv:
        with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                               ["isbn", "book_id", "existing_primary_source",
                                "jaccard", "existing_coverage", "old_nodes",
                                "cand_nodes", "kind"])
            w.writeheader()
            w.writerows(rows)

    md = [
        "# legallib 保護衝突レビュー トリアージ",
        "",
        f"- 対象: {len(rows)} 件",
        f"- 分類: {dict(kinds)}",
        f"- 既存ソース内訳: {dict(srcs)}",
        "",
        "| isbn | 既存src | 分類 | jaccard | 既存被覆 | 旧→候補 |",
        "|---|---|---|---|---|---|",
        *[f"| {r['isbn']} | {r['existing_primary_source']} | {r['kind']} | "
          f"{r['jaccard']} | {r['existing_coverage']} | {r['old_nodes']}→{r['cand_nodes']} |"
          for r in rows[:50]],
    ]
    md_text = "\n".join(md) + "\n"
    if args.out_md:
        Path(args.out_md).write_text(md_text, encoding="utf-8")
    print(f"triaged={len(rows)} kinds={dict(kinds)}")
    if not args.out_md:
        print(md_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
