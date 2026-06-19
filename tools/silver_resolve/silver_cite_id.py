#!/usr/bin/env python3
"""silver-1: 掲載位置文字列 -> 判例ID の silver 解決 (read-only dry-run).

WO-SILVER-CITEID-001 の実装. 依存ゼロ (Python 3.9+).

入力 (read-only, 既取得データのみ):
  --lic-edges     lic 解説引用エッジ JSONL
                  via_journal: {"edge_id","edge_type":"cites_judgment_via_journal","source_locator":"journal_article:労働判例:1060:5"}
                  by_date    : {"edge_id","edge_type":"cites_judgment_by_date","court":"最高裁","date":"1994-07-18"}
  --pub-index     hanrei_published_in 索引 JSONL
                  {"hanrei_id":"27824765","journal":"労働判例","issue":"1060","page":"5"}
  --canon-index   (任意) 判例 canonical 索引 JSONL (by_date 解決用)
                  {"hanrei_id":"27824765","court":"最高裁","date":"1994-07-18"}
  --norm-dict     (任意) 誌名正規化辞書 JSON {"労判":"労働判例", ...}

出力 (candidate staging のみ. 本番 write なし):
  <out>/silver_cite_resolution_candidates.jsonl
  <out>/silver_cite_resolution_report.md

本ツールは read-only: 入力 JSONL/索引の集計・突合のみ. DB write / 外部取得 / canonical mint なし.
strong = issue_page_exact かつ単一候補 (D2: strong-only). それ以外は review queue へ.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

STRONG_THRESHOLD = 0.90
_FW_DIGITS = {ord("０") + i: ord("0") + i for i in range(10)}


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def normalize_journal(raw: str, norm_dict: Optional[Dict[str, str]] = None) -> str:
    """誌名正規化: 全半角・空白を吸収し, 辞書で canonical へ寄せる."""
    if raw is None:
        return ""
    s = raw.translate(_FW_DIGITS).replace("　", "").replace(" ", "").strip()
    if norm_dict and s in norm_dict:
        return norm_dict[s]
    return s


def parse_locator(locator: str) -> Optional[Tuple[str, str, str]]:
    """'journal_article:労働判例:1060:5' -> (journal, issue, page). 解析不能は None."""
    if not locator:
        return None
    parts = locator.split(":")
    if parts and parts[0] == "journal_article":
        parts = parts[1:]
    if len(parts) < 3:
        return None
    journal, issue, page = parts[0], parts[1], parts[2]
    if not journal or not issue:
        return None
    return journal, issue, page


def build_pub_indexes(pub_records: Iterable[dict], norm_dict: Optional[Dict[str, str]]):
    """(journal,issue,page)->[hid] と (journal,issue)->[hid] を構築."""
    by_jip: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    by_ji: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for r in pub_records:
        hid = str(r.get("hanrei_id", ""))
        if not hid:
            continue
        j = normalize_journal(r.get("journal", ""), norm_dict)
        issue = str(r.get("issue", "")).translate(_FW_DIGITS)
        page = str(r.get("page", "")).translate(_FW_DIGITS)
        by_jip[(j, issue, page)].append(hid)
        by_ji[(j, issue)].append(hid)
    return by_jip, by_ji


def build_canon_index(canon_records: Iterable[dict]):
    by_cd: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for r in canon_records:
        hid = str(r.get("hanrei_id", ""))
        if not hid:
            continue
        by_cd[(str(r.get("court", "")).strip(), str(r.get("date", "")).strip())].append(hid)
    return by_cd


def resolve_edge(edge: dict, by_jip, by_ji, by_cd, norm_dict) -> dict:
    """1 エッジを解決. candidate dict を返す (resolved_hanrei_id は list)."""
    etype = edge.get("edge_type", "")
    base = {
        "lic_edge_id": edge.get("edge_id", ""),
        "edge_type": etype,
        "resolved_hanrei_id": [],
        "match_method": None,
        "confidence": 0.0,
        "decision_status": "unresolved",
        "evidence": None,
        "honest_empty": None,
    }

    if etype == "cites_judgment_via_journal":
        locator = edge.get("source_locator", "")
        base["source_locator_raw"] = locator
        parsed = parse_locator(locator)
        if parsed is None:
            base["honest_empty"] = "locator_unresolvable"
            return base
        journal, issue, page = parsed
        nj = normalize_journal(journal, norm_dict)
        base["normalized_journal"], base["issue"], base["page"] = nj, issue, page
        # L1 issue+page exact
        hits = by_jip.get((nj, issue, str(page).translate(_FW_DIGITS)), [])
        if len(hits) == 1:
            base.update(resolved_hanrei_id=hits, match_method="issue_page_exact",
                        confidence=0.95, decision_status="strong",
                        evidence=f"{nj}:{issue}:{page}")
            return base
        if len(hits) > 1:
            base.update(resolved_hanrei_id=sorted(set(hits)), match_method="issue_page_exact",
                        confidence=0.60, decision_status="review",
                        evidence=f"{nj}:{issue}:{page} (多候補{len(hits)})")
            return base
        # L2 issue-level fallback (頁ロス)
        fb = by_ji.get((nj, issue), [])
        if fb:
            base.update(resolved_hanrei_id=sorted(set(fb)), match_method="issue_page_fallback",
                        confidence=0.50, decision_status="review",
                        evidence=f"{nj}:{issue} (号fallback {len(set(fb))}候補)")
            return base
        base["honest_empty"] = "db_unbuilt"  # 索引に該当掲載位置なし
        return base

    if etype == "cites_judgment_by_date":
        court = str(edge.get("court", "")).strip()
        date = str(edge.get("date", "")).strip()
        base["evidence"] = f"{court}/{date}"
        hits = by_cd.get((court, date), [])
        if len(hits) == 1:
            base.update(resolved_hanrei_id=hits, match_method="court_date",
                        confidence=0.80, decision_status="review")  # court+date は衝突あり -> review
            return base
        if len(hits) > 1:
            base.update(resolved_hanrei_id=sorted(set(hits)), match_method="court_date",
                        confidence=0.55, decision_status="review",
                        evidence=f"{court}/{date} (多候補{len(hits)})")
            return base
        base["honest_empty"] = "db_unbuilt"
        return base

    base["honest_empty"] = "unknown_edge_type"
    return base


def resolve_all(edges, by_jip, by_ji, by_cd, norm_dict) -> List[dict]:
    return [resolve_edge(e, by_jip, by_ji, by_cd, norm_dict) for e in edges]


def build_report(cands: List[dict]) -> str:
    total = len(cands)
    by_method = Counter(c["match_method"] or "(none)" for c in cands)
    by_status = Counter(c["decision_status"] for c in cands)
    empties = Counter(c["honest_empty"] for c in cands if c["honest_empty"])
    resolved = sum(1 for c in cands if c["resolved_hanrei_id"])
    strong = by_status.get("strong", 0)
    rate = (resolved / total * 100) if total else 0.0
    lines = [
        "# silver-1 掲載位置→判例ID 解決レポート (dry-run / read-only)",
        "",
        f"- 入力エッジ総数: **{total}**",
        f"- 解決済 (≥1候補): **{resolved}** ({rate:.1f}%)  ※基準値 概算24%",
        f"- strong (issue_page_exact 単一): **{strong}**  ← D2: これのみ staging write 候補",
        f"- review queue: **{by_status.get('review', 0)}**",
        f"- 未解決 (honest_empty): **{by_status.get('unresolved', 0)}**",
        "",
        "## match_method 別",
        "| method | 件数 |",
        "|---|---|",
    ]
    for m, n in by_method.most_common():
        lines.append(f"| {m} | {n} |")
    lines += ["", "## 未解決理由 (honest_empty)", "| reason | 件数 |", "|---|---|"]
    for r, n in empties.most_common():
        lines.append(f"| {r} | {n} |")
    lines += [
        "",
        "## 二層分離の確認",
        f"- strong は issue_page_exact 単一のみ ({strong}). fallback/court_date/多候補は review.",
        "- strong と review は別レーン. review は自動確定しない (P4 信号保存).",
        "",
        "_本レポートは dry-run. candidate は staging 出力のみ. 本番 write なし._",
    ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="silver-1 掲載位置→判例ID 解決 (read-only dry-run)")
    ap.add_argument("--lic-edges", required=True, type=Path)
    ap.add_argument("--pub-index", required=True, type=Path)
    ap.add_argument("--canon-index", type=Path, default=None)
    ap.add_argument("--norm-dict", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    norm_dict = json.loads(args.norm_dict.read_text(encoding="utf-8")) if args.norm_dict else None
    by_jip, by_ji = build_pub_indexes(read_jsonl(args.pub_index), norm_dict)
    by_cd = build_canon_index(read_jsonl(args.canon_index)) if args.canon_index else {}
    cands = resolve_all(read_jsonl(args.lic_edges), by_jip, by_ji, by_cd, norm_dict)

    args.out.mkdir(parents=True, exist_ok=True)
    cpath = args.out / "silver_cite_resolution_candidates.jsonl"
    with cpath.open("w", encoding="utf-8") as fh:
        for c in cands:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    rpath = args.out / "silver_cite_resolution_report.md"
    rpath.write_text(build_report(cands), encoding="utf-8")
    print(f"[silver-1] candidates={len(cands)} -> {cpath}")
    print(f"[silver-1] report -> {rpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
