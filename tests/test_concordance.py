"""concordance / conflict_detector / review_report のテスト (v0.3.1 report-only).

all_nodes_accounted_for / matched・orphan 分類 / 各 conflict パターン /
book-level risk 判定 を合成ケースで固定。stdlib のみ。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from concordance import build_concordance, numbering_scheme  # noqa: E402
from conflict_detector import detect_conflicts, unresolved_count  # noqa: E402
from concordance_report import _demo_books, run_report  # noqa: E402
from review_report import book_summary  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _n(t, d=1, p=None):
    return {"title": t, "depth": d, "page_start": p}


def test_concordance_accounting() -> None:
    sources = {
        "legallib": [_n("第1章 序論"), _n("第2章 当事者"), _n("独自付録")],
        "bencom": [_n("第1章 序論"), _n("第2章 当事者")],
    }
    conc = build_concordance(sources)
    check(conc["all_nodes_accounted_for"], "全ノード accounted")
    check(conc["accounting"]["total_nodes"] == 5, "総ノード5")
    kinds = {c["title_norm"]: c["kind"] for c in conc["clusters"]}
    # 第1章/第2章は2ソース→matched, 独自付録は1ソース→orphan
    import_norm = build_concordance({"x": [_n("第1章 序論")]})["clusters"][0]["title_norm"]
    check(any(c["kind"] == "matched" for c in conc["clusters"]), "matched あり")
    check(any(c["kind"] == "orphan" for c in conc["clusters"]), "orphan あり")
    matched_total = conc["accounting"]["matched"]
    orphan_total = conc["accounting"]["orphan"]
    check(matched_total == 4 and orphan_total == 1, "matched4/orphan1")


def test_repeated_heading() -> None:
    sources = {"legallib": [_n("総論"), _n("第1章"), _n("総論")]}  # 総論が正当反復
    conc = build_concordance(sources)
    check(conc["repeated_headings"].get("legallib", {}).get(
        build_concordance({"x": [_n("総論")]})["clusters"][0]["title_norm"]) == 2,
        "総論の反復を記録")
    confs = detect_conflicts(conc, {"legallib": {}})
    rep = [c for c in confs if c["pattern"] == "same_heading_repeated_legitimately"]
    check(rep and rep[0]["resolved"], "正当反復は resolved (apply ブロックしない)")


def test_conflict_patterns() -> None:
    # coverage_mismatch + edition_mismatch(別版)
    sources = {"a": [_n("総論")], "b": [_n("総論"), _n("X", 1), _n("Y", 1), _n("Z", 1), _n("W", 1)]}
    meta = {"a": {"isbn": "9784000000010", "title": "民法", "year": "2015", "page_count": 200},
            "b": {"isbn": "9784000000027", "title": "民法", "year": "2022", "page_count": 400}}
    confs = detect_conflicts(build_concordance(sources), meta)
    pats = {c["pattern"] for c in confs}
    check("coverage_mismatch" in pats, "coverage_mismatch 検出")
    check("edition_mismatch_suspected" in pats, "edition_mismatch 検出 (別ISBN/年/頁)")
    check(unresolved_count(confs) >= 2, "unresolved 2件以上")

    # page_basis_mismatch
    confs2 = detect_conflicts(
        build_concordance({"a": [_n("総論")], "b": [_n("総論")]}),
        {"a": {"page_basis": "print_page"}, "b": {"page_basis": "pdf_page"}})
    check(any(c["pattern"] == "page_basis_mismatch" for c in confs2), "page_basis_mismatch 検出")

    # partial_toc (min depth>1)
    confs3 = detect_conflicts(build_concordance({"a": [_n("第1節", 2), _n("第2節", 2)]}), {"a": {}})
    check(any(c["pattern"] == "partial_toc_source" for c in confs3), "partial_toc 検出")

    # numbering_scheme_changed
    confs4 = detect_conflicts(
        build_concordance({"a": [_n("第1章 X")], "b": [_n("第一章 X")]}), {"a": {}, "b": {}})
    check(any(c["pattern"] == "numbering_scheme_changed" for c in confs4), "numbering 体系差 検出")


def test_numbering_scheme() -> None:
    check(numbering_scheme("第1章 総則") == "kanji_chapter", "第1章→kanji_chapter")
    check(numbering_scheme("第一章 総則") == "kanji_num", "第一章→kanji_num")
    check(numbering_scheme("Ⅰ 序") == "roman", "Ⅰ→roman")
    check(numbering_scheme("ふつうの見出し") is None, "番号なし→None")


def test_book_summary_risk() -> None:
    books = _demo_books()
    by = {b["isbn"]: b for b in books}
    low = book_summary(*[by["9784000000010"][k] for k in ("isbn", "title")],
                       by["9784000000010"]["sources"], by["9784000000010"]["source_meta"])
    check(low["risk"] == "low" and low["conflicts"]["unresolved"] == 0, "一致本は low risk")
    check(low["all_nodes_accounted_for"], "low本 accounted")

    high = book_summary(*[by["9784000000034"][k] for k in ("isbn", "title")],
                        by["9784000000034"]["sources"], by["9784000000034"]["source_meta"])
    check(high["risk"] == "high", "別版疑い本は high risk")
    check(high["edition_identity_status"] == "suspected_different_manifestation", "別版判定")
    check("approve" not in high["recommended_action"].split(";")[0].lower()
          or "do not" in high["recommended_action"].lower(), "high は承認推奨しない")


def test_report_only_run() -> None:
    result = run_report(_demo_books())
    check(result["report_only"] and result["final_toc_written"] is False, "report-only/未書込")
    check(set(result["risk_counts"]) <= {"low", "medium", "high"}, "risk 集計")
    check(len(result["summaries"]) == 3, "3冊サマリ")
    with tempfile.TemporaryDirectory() as td:
        from concordance_report import write_report
        write_report(result, Path(td))
        rep = (Path(td) / "report.md").read_text(encoding="utf-8")
        check("final_toc" in rep and "report-only" in rep, "report.md に report-only 明記")
        check((Path(td) / "conflicts.jsonl").exists(), "conflicts.jsonl 出力")


def main() -> int:
    for t in [test_concordance_accounting, test_repeated_heading, test_conflict_patterns,
              test_numbering_scheme, test_book_summary_risk, test_report_only_run]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
