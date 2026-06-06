#!/usr/bin/env python3
"""雑誌目次 JSON を全数スイープして論文 entity を抽出する (指示書 §7 STEP A2).

Usage:
    python scripts/run_article_parser.py --src <dir-of-journal-json> --out <out-dir>

入力 dir 内の *.json を走査し、content_type=="journal" のものを対象に
  - articles_extracted.jsonl        (§4.1)
  - articles_extracted_summary.csv  (§4.4)
  - articles_unknown_sample.csv     (§4.5)
を書き出す。content_type フィールドが無い JSON は、toc を持つものを journal
とみなす (フォールバック)。

出力順は journal_book_id 昇順 → ordinal 昇順 (冪等性確保, §4.3)。
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.article_parser import VALID_KINDS, parse_journal  # noqa: E402


def _sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_journal(doc: dict) -> bool:
    ct = doc.get("content_type")
    if ct is not None:
        return ct == "journal"
    # フォールバック: toc 系キーを持てば journal 扱い
    return any(k in doc for k in ("toc", "nodes", "contents"))


def _parse_rate(article: int, unknown: int):
    denom = article + unknown
    return (article / denom) if denom else None


def sweep(src_dir: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(src_dir, "*.json")))

    all_rows: list[dict] = []
    summary: list[dict] = []
    skipped: list[str] = []

    for path in paths:
        book_id = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:  # noqa: BLE001
            skipped.append(f"{book_id}: load error {e}")
            continue
        if not isinstance(doc, dict) or not _is_journal(doc):
            continue

        # 例外が出ても journal 単位で fail させない (§5.1)
        try:
            rows = parse_journal(doc, book_id)
        except Exception as e:  # noqa: BLE001
            rows = [{
                "journal_book_id": book_id,
                "journal_title": doc.get("title", ""),
                "ordinal": 1, "level": 1, "kind": "unknown",
                "section": None, "title": None, "authors_raw": None,
                "authors": None, "series_tag": None, "page_start": None,
                "raw_label": f"__PARSE_ERROR__ {e}",
            }]
        all_rows.extend(rows)

        counts = {k: 0 for k in VALID_KINDS}
        for r in rows:
            counts[r["kind"]] = counts.get(r["kind"], 0) + 1
        summary.append({
            "journal_book_id": book_id,
            "total_nodes": len(rows),
            "article_count": counts["article"],
            "section_header_count": counts["section_header"],
            "other_count": counts["other"],
            "unknown_count": counts["unknown"],
            "parse_rate": _parse_rate(counts["article"], counts["unknown"]),
            "journal_title": doc.get("title", ""),
        })

    # 冪等な出力順 (§4.3)
    all_rows.sort(key=lambda r: (r["journal_book_id"], r["ordinal"]))
    summary.sort(key=lambda r: r["journal_book_id"])

    # --- articles_extracted.jsonl ---
    jsonl_path = os.path.join(out_dir, "articles_extracted.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in all_rows:
            out = {k: v for k, v in r.items() if k != "journal_title"}
            out = {
                "journal_book_id": r["journal_book_id"],
                "journal_title": r["journal_title"],
                "ordinal": r["ordinal"],
                "level": r["level"],
                "kind": r["kind"],
                "section": r["section"],
                "title": r["title"],
                "authors_raw": r["authors_raw"],
                "authors": r["authors"],
                "series_tag": r["series_tag"],
                "page_start": r["page_start"],
                "raw_label": r["raw_label"],
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    # --- articles_extracted_summary.csv ---
    summary_path = os.path.join(out_dir, "articles_extracted_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["journal_book_id", "total_nodes", "article_count",
                    "section_header_count", "other_count", "unknown_count",
                    "parse_rate"])
        for r in summary:
            pr = "" if r["parse_rate"] is None else f"{r['parse_rate']:.4f}"
            w.writerow([r["journal_book_id"], r["total_nodes"], r["article_count"],
                        r["section_header_count"], r["other_count"],
                        r["unknown_count"], pr])

    # --- articles_unknown_sample.csv (§4.5) ---
    unknown_path = os.path.join(out_dir, "articles_unknown_sample.csv")
    low = [r for r in summary if r["parse_rate"] is not None and r["parse_rate"] < 0.95]
    low.sort(key=lambda r: r["parse_rate"])
    rows_by_book = {}
    for r in all_rows:
        rows_by_book.setdefault(r["journal_book_id"], []).append(r)
    with open(unknown_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["journal_book_id", "journal_title", "ordinal", "raw_label"])
        dumped = 0
        for r in low:
            if dumped >= 50:
                break
            unk = [x for x in rows_by_book.get(r["journal_book_id"], [])
                   if x["kind"] == "unknown"][:5]
            for x in unk:
                if dumped >= 50:
                    break
                w.writerow([x["journal_book_id"], x["journal_title"],
                            x["ordinal"], x["raw_label"]])
                dumped += 1

    # --- 集計 ---
    tot_article = sum(r["article_count"] for r in summary)
    tot_unknown = sum(r["unknown_count"] for r in summary)
    tot_section = sum(r["section_header_count"] for r in summary)
    tot_other = sum(r["other_count"] for r in summary)
    overall = _parse_rate(tot_article, tot_unknown)

    return {
        "journals": len(summary),
        "skipped": skipped,
        "total_article": tot_article,
        "total_section_header": tot_section,
        "total_other": tot_other,
        "total_unknown": tot_unknown,
        "overall_parse_rate": overall,
        "outputs": {
            "jsonl": (jsonl_path, _sha1(jsonl_path)),
            "summary_csv": (summary_path, _sha1(summary_path)),
            "unknown_csv": (unknown_path, _sha1(unknown_path)),
        },
        "summary_rows": summary,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, help="雑誌 JSON のディレクトリ (legallib_dl)")
    ap.add_argument("--out", required=True, help="出力ディレクトリ")
    args = ap.parse_args()

    stats = sweep(args.src, args.out)
    print(f"journals processed : {stats['journals']}")
    print(f"  article          : {stats['total_article']}")
    print(f"  section_header   : {stats['total_section_header']}")
    print(f"  other            : {stats['total_other']}")
    print(f"  unknown          : {stats['total_unknown']}")
    pr = stats["overall_parse_rate"]
    print(f"  overall parse_rate: {pr:.4f}" if pr is not None else "  overall parse_rate: n/a")
    print(f"  hard gate (>=0.80): {'PASS' if (pr or 0) >= 0.80 else 'FAIL'}")
    print(f"  soft gate (>=0.90): {'PASS' if (pr or 0) >= 0.90 else 'MISS'}")
    for label, (path, sha) in stats["outputs"].items():
        print(f"  {label}: {path}  sha1={sha}")
    if stats["skipped"]:
        print("skipped:", *stats["skipped"], sep="\n  ")


if __name__ == "__main__":
    main()
