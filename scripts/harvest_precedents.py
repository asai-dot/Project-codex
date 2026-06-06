#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harvest_precedents.py — ベンコム「引用判例リンク」ページ → 判例引用レコード

入力: precedents ページ（library.bengo4.com/books/{cid}/precedents#page_{N}）の
      本文テキスト（ログインが要るので、保存HTML/テキスト or 認証付き取得を人/env側で用意）。
出力: cases（正規化判例）と citations（文献ページ→判例 エッジ）。

ページ構造（観測）:
  「83ページ 紙面43ページ」     ← viewer_page / print_page
  東京高等裁判所 昭和43年8月6日   ← 裁判所 + 和暦判決日
  昭和43年（ラ）第557号          ← 事件番号
  訴状却下命令に対する即時抗告事件 ← 事件名
  捕捉しがたい…事例              ← 判示事項/要旨

regexで頑健に拾う（HTMLタグに依存しない＝採取経路が変わっても動く）。

使い方:
  python3 scripts/harvest_precedents.py --cid ebaaf... [--viewer-page 83] < precedents.txt
  cat precedents.txt | python3 scripts/harvest_precedents.py --cid ebaaf... --out-dir data
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.case_identity import normalize_citation, parse_date  # noqa: E402

COURT_DATE_RE = re.compile(r"(.+?裁判所.*?)\s*((?:明治|大正|昭和|平成|令和)\s*(?:元|\d+)\s*年\s*\d+\s*月\s*\d+\s*日)")
CASENO_RE = re.compile(r"((?:明治|大正|昭和|平成|令和)?\s*(?:元|\d+)\s*年\s*[（(].+?[）)]\s*第?\s*\d+\s*号)")
HH_ID_RE = re.compile(r"\b(L\d{8})\b")
PAGE_RE = re.compile(r"(\d+)\s*ページ\s*紙面\s*(\d+)\s*ページ")


def harvest_text(text, cid, viewer_page=None, print_page=None):
    lines = [ln.strip() for ln in text.splitlines()]
    # ページ対応（「83ページ 紙面43ページ」）を拾う
    for ln in lines:
        m = PAGE_RE.search(ln)
        if m:
            viewer_page = viewer_page or int(m.group(1))
            print_page = print_page or int(m.group(2))
            break

    records = []
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        m = COURT_DATE_RE.search(ln)
        if not m or "裁判所" not in m.group(1):
            i += 1
            continue
        court = m.group(1).strip()
        date = m.group(2).strip()
        # 同一行/直後数行から 事件番号・事件名・要旨・L番号 を集める
        caseno = None
        title = None
        summary_parts = []
        hh_id = None
        j = i + 1
        block = []
        while j < n and not (COURT_DATE_RE.search(lines[j]) and "裁判所" in (COURT_DATE_RE.search(lines[j]).group(1))):
            if lines[j]:
                block.append(lines[j])
            j += 1
            if j - i > 8:   # 1判例ブロックの暴走防止
                break
        for b in block:
            if caseno is None and CASENO_RE.search(b):
                caseno = CASENO_RE.search(b).group(1).strip()
                continue
            if hh_id is None and HH_ID_RE.search(b):
                hh_id = HH_ID_RE.search(b).group(1)
            if title is None and not CASENO_RE.search(b):
                title = b
            elif b != title:
                summary_parts.append(b)
        rec = normalize_citation(court, date, caseno, title=title, hh_id=hh_id)
        rec["summary"] = " ".join(summary_parts) or None
        records.append(rec)
        i = j

    citations = []
    for r in records:
        citations.append({
            "cid": cid, "viewer_page": viewer_page, "print_page": print_page,
            "case_node_id": r["case_node_id"], "canonical_key": r["canonical_key"],
            "source": "bencom_precedents", "claim_scope": "cites", "review_status": "pending_review",
        })
    return {"cases": records, "citations": citations,
            "context": {"cid": cid, "viewer_page": viewer_page, "print_page": print_page}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cid", required=True)
    ap.add_argument("--viewer-page", type=int, default=None)
    ap.add_argument("--print-page", type=int, default=None)
    ap.add_argument("--out-dir", default=None, help="指定すると cases.jsonl / case_citations.jsonl を追記")
    args = ap.parse_args()
    text = sys.stdin.read()
    result = harvest_text(text, args.cid, args.viewer_page, args.print_page)
    if args.out_dir:
        d = Path(args.out_dir)
        d.mkdir(parents=True, exist_ok=True)
        with (d / "cases.jsonl").open("a", encoding="utf-8") as f:
            for c in result["cases"]:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        with (d / "case_citations.jsonl").open("a", encoding="utf-8") as f:
            for c in result["citations"]:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"cases={len(result['cases'])} citations={len(result['citations'])} → {d}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
