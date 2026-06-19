#!/usr/bin/env python3
"""silver-2: TOC 階層 -> 論点セクションの構造化 (read-only dry-run).

WO-SILVER-TOCSECTION-001 の実装. 依存ゼロ (Python 3.9+).

同一書籍 weight-1 の無意味な全結合共起を, 同一論点セクション (TOC subtree) 単位の
共起へ精緻化する. 論点見出し = 各判例行の最近接祖先 heading (=実務界が書いた論点タイトルの harvest).
人手 seed なし / D1#15 分野分類での代替なし (G_ELEMENT_PREDICATE_NOT_FIELD_CLASS).

入力 (read-only):
  --toc-nodes   TOC 階層 JSONL
                {"toc_node_id":"t2","parent_id":"t1","book_id":"b1","heading":"...","kind":"heading"}
                kind: "heading" | "row" (row = 判例を載せる行)
  --toc-edges   toc_row_reports_hanrei JSONL
                {"toc_node_id":"t3","hanrei_id":"27824765","book_id":"b1"}
  --hyoshaku    (任意) 評釈密度 JSONL {"hanrei_id":"27824765","hyoshaku_count":11}

出力 (candidate のみ. 本番 write なし):
  <out>/silver_toc_section_candidates.jsonl
  <out>/silver_issue_cooccurrence_candidates.jsonl
  <out>/silver_toc_section_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def nearest_heading(node_id: str, nodes: Dict[str, dict]) -> Optional[str]:
    """node から親方向に辿り, 最近接の kind=='heading' ノード id を返す (論点section)."""
    seen = set()
    cur = node_id
    while cur is not None and cur in nodes and cur not in seen:
        seen.add(cur)
        n = nodes[cur]
        if n.get("kind") == "heading":
            return cur
        cur = n.get("parent_id")
    return None


def resolve_sections(node_records: Iterable[dict], edge_records: Iterable[dict], hyoshaku: Dict[str, int]):
    """論点section ごとの member 判例を束ね, section候補・共起候補を作る."""
    nodes = {str(n["toc_node_id"]): n for n in node_records}

    # section_id -> set(hanrei), trace 用に row 解決状況も集計
    section_members: Dict[str, set] = defaultdict(set)
    section_heading: Dict[str, str] = {}
    section_book: Dict[str, str] = {}
    book_members: Dict[str, set] = defaultdict(set)  # naive 比較用 (同一書籍全結合)
    unresolved_rows = 0
    total_rows = 0

    for e in edge_records:
        total_rows += 1
        hid = str(e.get("hanrei_id", ""))
        row_id = str(e.get("toc_node_id", ""))
        book = str(e.get("book_id", ""))
        if hid and book:
            book_members[book].add(hid)
        sec = nearest_heading(row_id, nodes)
        if sec is None or not hid:
            unresolved_rows += 1
            continue
        section_members[sec].add(hid)
        section_heading[sec] = nodes[sec].get("heading", "")
        section_book[sec] = nodes[sec].get("book_id", book)

    # section candidates
    sec_cands = []
    for sec, members in section_members.items():
        sec_cands.append({
            "issue_section_id": sec,
            "section_heading": section_heading.get(sec, ""),  # 論点タイトル (harvest)
            "book_id": section_book.get(sec, ""),
            "member_hanrei_ids": sorted(members),
            "member_count": len(members),
            "decision_status": "strong" if any(hyoshaku.get(h, 0) > 0 for h in members) else "review",
            "evidence": f"section heading harvest; {len(members)} members",
            "honest_empty": None,
        })

    # 論点section 共起 (section 内ペアのみ; 同一書籍全結合は採らない)
    pair_sections: Dict[Tuple[str, str], set] = defaultdict(set)
    for sec, members in section_members.items():
        for a, b in combinations(sorted(members), 2):
            pair_sections[(a, b)].add(sec)
    co_cands = []
    for (a, b), secs in pair_sections.items():
        imp = (hyoshaku.get(a, 0) + hyoshaku.get(b, 0))
        co_cands.append({
            "hanrei_a": a, "hanrei_b": b,
            "shared_section_ids": sorted(secs),
            "pair_weight": len(secs),          # 共有論点section 数
            "importance": imp,                 # 評釈密度合計 (harvest. 人手重み付けなし)
            "decision_status": "strong" if imp > 0 else "review",
        })

    # naive 同一書籍全結合ペア数 (置換前の無意味共起の規模)
    naive_pairs = sum(len(m) * (len(m) - 1) // 2 for m in book_members.values())

    stats = {
        "total_rows": total_rows,
        "unresolved_rows": unresolved_rows,
        "sections": len(sec_cands),
        "section_pairs": len(co_cands),
        "naive_book_pairs": naive_pairs,
    }
    return sec_cands, co_cands, stats


def build_report(sec_cands, co_cands, stats) -> str:
    sizes = Counter()
    for s in sec_cands:
        b = s["member_count"]
        bucket = "1" if b == 1 else "2-5" if b <= 5 else "6-20" if b <= 20 else "21+"
        sizes[bucket] += 1
    wdist = Counter(c["pair_weight"] for c in co_cands)
    trace_absent = sum(1 for s in sec_cands if s["decision_status"] == "review")
    lines = [
        "# silver-2 TOC→論点section 構造化レポート (dry-run / read-only)",
        "",
        f"- 入力 row (toc_row_reports_hanrei): **{stats['total_rows']}**",
        f"- 論点section 解決不能 row: **{stats['unresolved_rows']}**",
        f"- 抽出 論点section: **{stats['sections']}**",
        "",
        "## 無意味共起の置換 (本ツールの主眼)",
        f"- 同一書籍 全結合ペア (naive, weight-1, 無意味): **{stats['naive_book_pairs']}**",
        f"- 論点section 単位ペア (意味あり): **{stats['section_pairs']}**",
        "- → 書籍粒度の weight-1 全結合を捨て, 論点section 内共起のみ残した.",
        "",
        "## 論点section サイズ分布",
        "| member数 | section数 |",
        "|---|---|",
    ]
    for k in ["1", "2-5", "6-20", "21+"]:
        if sizes.get(k):
            lines.append(f"| {k} | {sizes[k]} |")
    lines += ["", "## 共起ペア weight (共有論点section数) 分布", "| weight | ペア数 |", "|---|---|"]
    for w, n in sorted(wdist.items()):
        lines.append(f"| {w} | {n} |")
    lines += [
        "",
        "## harvest / honest_empty 規律",
        f"- 論点見出しは文献TOC heading の harvest (人手 seed なし / 分野分類代替なし).",
        f"- 評釈密度ゼロ section = review ({trace_absent}). trace_absent として honest_empty 区別.",
        "- DD-LRINDEX-001 v0.4 (G_HARVEST_NOT_MANUFACTURE) GPT確認パス前は accepted 論点扱いしない.",
        "",
        "_本レポートは dry-run. candidate は staging 出力のみ. 本番 write なし._",
    ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="silver-2 TOC→論点section 構造化 (read-only dry-run)")
    ap.add_argument("--toc-nodes", required=True, type=Path)
    ap.add_argument("--toc-edges", required=True, type=Path)
    ap.add_argument("--hyoshaku", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    hyoshaku: Dict[str, int] = {}
    if args.hyoshaku:
        for r in read_jsonl(args.hyoshaku):
            hyoshaku[str(r.get("hanrei_id", ""))] = int(r.get("hyoshaku_count", 0))

    sec_cands, co_cands, stats = resolve_sections(
        read_jsonl(args.toc_nodes), read_jsonl(args.toc_edges), hyoshaku)

    args.out.mkdir(parents=True, exist_ok=True)
    sp = args.out / "silver_toc_section_candidates.jsonl"
    with sp.open("w", encoding="utf-8") as fh:
        for c in sec_cands:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    cp = args.out / "silver_issue_cooccurrence_candidates.jsonl"
    with cp.open("w", encoding="utf-8") as fh:
        for c in co_cands:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    rp = args.out / "silver_toc_section_report.md"
    rp.write_text(build_report(sec_cands, co_cands, stats), encoding="utf-8")
    print(f"[silver-2] sections={len(sec_cands)} pairs={len(co_cands)} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
