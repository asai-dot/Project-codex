"""concordance_report — v0.3.1 Phase 0/A の report-only 出口 (DDLEGALLIBCONCORD)。

複数ソース TOC から book-level conflict summary を生成するだけ。**final_toc は作らず、
apply もしない**。GPT 指定: 最初の deliverable は inventory と conflict report であり、
final_toc 生成ではない。

入力 (JSON): 各 book = {isbn, title, source_meta:{src:{...bib+page_basis}}, sources:{src:[nodes]}}。
出力: report.md (book summary 2層) + conflicts.jsonl + summary.json。本番書き込みなし。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from concordance import CONCORDANCE_VERSION  # noqa: E402
from conflict_detector import CONFLICT_DETECTOR_VERSION  # noqa: E402
from page_basis import PAGE_BASIS_VERSION  # noqa: E402
from review_report import book_summary, render_book_summary_md  # noqa: E402

# report 出力に刻む pipeline version (GPT note: version stamp)。
PIPELINE_VERSIONS = {
    "concordance": CONCORDANCE_VERSION,
    "conflict_detector": CONFLICT_DETECTOR_VERSION,
    "page_basis": PAGE_BASIS_VERSION,
}


def run_report(books: list[dict]) -> dict:
    summaries = []
    conflicts_rows = []
    for b in books:
        s = book_summary(b["isbn"], b.get("title", ""), b["sources"], b.get("source_meta", {}))
        summaries.append(s)
        for c in s.pop("_conflicts_detail", []):
            conflicts_rows.append({"isbn": b["isbn"], **c})
    risk = Counter(s["risk"] for s in summaries)
    consensus_excluded = sum(s.get("consensus_excluded_sources", 0) for s in summaries)
    return {"summaries": summaries, "conflicts": conflicts_rows,
            "risk_counts": dict(risk),
            "versions": PIPELINE_VERSIONS,
            "consensus_excluded_sources_total": consensus_excluded,
            "report_only": True, "final_toc_written": False}


def write_report(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "conflicts.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["conflicts"]),
        encoding="utf-8")
    (out_dir / "summary.json").write_text(
        json.dumps({"versions": result["versions"], "risk_counts": result["risk_counts"],
                    "consensus_excluded_sources_total": result["consensus_excluded_sources_total"],
                    "summaries": result["summaries"]}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    lines = ["# legallibjoin concordance report (report-only / final_toc 未生成)", "",
             f"- versions: {result['versions']}",
             f"- books: {len(result['summaries'])}",
             f"- risk: {result['risk_counts']}",
             f"- consensus 除外 source (provenance_origin 未宣言): "
             f"{result['consensus_excluded_sources_total']}", "",
             "> これは concordance/conflict report であり final_toc apply ではない。",
             "> `pdf_primary` は絶対真理ではなく qualified PDF observation を意味する。",
             "> production apply は apply_guard の7 gate (whitelist/conflict/edition/PDF/"
             "rollback/decision_log/accounting) 通過後のみ。", ""]
    for s in result["summaries"]:
        lines.append(render_book_summary_md(s))
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _demo_books() -> list[dict]:
    def node(t, d=1, p=None):
        return {"title": t, "depth": d, "page_start": p}
    return [
        {  # 低リスク: 2ソース一致・矛盾なし
            "isbn": "9784000000010", "title": "国際取引法",
            "source_meta": {
                "legallib": {"isbn": "9784000000010", "title": "国際取引法", "publisher": "有斐閣", "year": "2018", "page_count": 380, "page_basis": "print_page"},
                "bencom": {"isbn": "9784000000010", "title": "国際取引法", "publisher": "有斐閣", "year": "2018", "page_count": 384, "page_basis": "print_page"}},
            "sources": {
                "legallib": [node("第1章 序論", 1, 1), node("第1節 意義", 2, 1), node("第2章 当事者", 1, 50)],
                "bencom": [node("第1章 序論", 1, 1), node("第1節 意義", 2, 1), node("第2章 当事者", 1, 50)]},
        },
        {  # 中リスク: coverage mismatch (片方が極端に少ない)
            "isbn": "9784000000027", "title": "会社法",
            "source_meta": {
                "openbd": {"isbn": "9784000000027", "title": "会社法", "publisher": "X", "year": "2020", "page_count": 600, "page_basis": "print_page"},
                "legallib": {"isbn": "9784000000027", "title": "会社法", "publisher": "X", "year": "2020", "page_count": 600, "page_basis": "pdf_page"}},
            "sources": {
                "openbd": [node("総論", 1)],
                "legallib": [node("総論", 1), node("第1編 設立", 1), node("第1章", 2), node("第2章", 2), node("第2編 株式", 1)]},
        },
        {  # 高リスク: 別版疑い (ISBN/年/ページ差)
            "isbn": "9784000000034", "title": "民法",
            "source_meta": {
                "legallib": {"isbn": "9784000000034", "title": "民法", "publisher": "Y", "year": "2015", "page_count": 400, "page_basis": "print_page"},
                "bencom": {"isbn": "9784000000041", "title": "民法", "publisher": "Y", "year": "2022", "page_count": 480, "page_basis": "print_page"}},
            "sources": {
                "legallib": [node("第1章 総則", 1), node("第2章 物権", 1)],
                "bencom": [node("第1章 総則", 1), node("第2章 物権", 1), node("第3章 債権", 1)]},
        },
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="v0.3.1 concordance report (report-only)")
    ap.add_argument("--books", help="books JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)

    books = _demo_books() if args.demo else json.loads(Path(args.books).read_text(encoding="utf-8"))
    result = run_report(books)
    write_report(result, Path(args.out))
    print(json.dumps(result["risk_counts"], ensure_ascii=False, sort_keys=True))
    print(f"report: {Path(args.out) / 'report.md'} (report-only, final_toc 未生成)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
