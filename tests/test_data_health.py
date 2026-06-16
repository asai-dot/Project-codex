"""thresholds + data_health テスト (report-only 足場)。

- thresholds: 既定/override マージ、壊れた config を無視、_meta キー除外。
- data_health: 3層スコア、defect 検出、修復ルート分類、corpus 集計、本番未書込。
stdlib のみ。
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from data_health import book_health, corpus_health  # noqa: E402
from review_report import book_summary  # noqa: E402
from thresholds import DEFAULTS, load_thresholds  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _clean_book() -> dict:
    return {
        "isbn": "9784000000010", "title": "国際取引法",
        "source_meta": {
            "legallib": {"isbn": "9784000000010", "title": "国際取引法", "publisher": "有斐閣",
                         "year": "2018", "page_count": 380, "page_basis": "print_page",
                         "source_sha256": "abc", "provenance_origin": "legallib"},
            "bencom": {"isbn": "9784000000010", "title": "国際取引法", "publisher": "有斐閣",
                       "year": "2018", "page_count": 384, "page_basis": "print_page",
                       "source_sha256": "def", "provenance_origin": "bencom"}},
        "sources": {
            "legallib": [{"title": "第1章 序論", "depth": 1, "page_start": 1},
                         {"title": "第1節 意義", "depth": 2, "page_start": 1},
                         {"title": "第2章 当事者", "depth": 1, "page_start": 50},
                         {"title": "第3章 契約", "depth": 1, "page_start": 90},
                         {"title": "第4章 紛争", "depth": 1, "page_start": 140}],
            "bencom": [{"title": "第1章 序論", "depth": 1, "page_start": 1},
                       {"title": "第1節 意義", "depth": 2, "page_start": 1},
                       {"title": "第2章 当事者", "depth": 1, "page_start": 50},
                       {"title": "第3章 契約", "depth": 1, "page_start": 90},
                       {"title": "第4章 紛争", "depth": 1, "page_start": 140}]},
    }


def _dirty_book() -> dict:
    return {
        "isbn": "9784000000099", "title": "汚いデータ本",
        "source_meta": {
            "legallib": {"isbn": "9784000000099", "title": "汚いデータ本"}},  # year/pub/sha/basis 欠落
        "sources": {
            "legallib": [{"title": "第1章", "depth": 1}]},  # 単一・flat・sparse
    }


def test_thresholds() -> None:
    t = load_thresholds()
    check(t["coverage_mismatch_ratio"] == 3.0, "既定 coverage ratio=3.0")
    check(t["health"]["weight_l2_toc"] == 40, "既定 health weight l2=40")
    # override が最優先
    t2 = load_thresholds(override={"coverage_mismatch_ratio": 5.0})
    check(t2["coverage_mismatch_ratio"] == 5.0, "override 反映")
    check(DEFAULTS["coverage_mismatch_ratio"] == 3.0, "DEFAULTS は不変")
    # 壊れた config は無視して既定で動く
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        t3 = load_thresholds(bad)
        check(t3["coverage_mismatch_ratio"] == 3.0, "壊れた config を無視")
    # _meta キーはマージされない
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "c.json"
        cfg.write_text(json.dumps({"_comment": "x", "edition_page_tolerance": 0.25}), encoding="utf-8")
        t4 = load_thresholds(cfg)
        check("_comment" not in t4, "_meta キー除外")
        check(t4["edition_page_tolerance"] == 0.25, "config 値で上書き")


def test_book_health() -> None:
    clean = book_health(_clean_book())
    dirty = book_health(_dirty_book())
    check(clean["health_score"] > dirty["health_score"], "綺麗な本 > 汚い本")
    check(clean["health_score"] >= 90, f"綺麗な本は高 health (got {clean['health_score']})")
    check(clean["defects"] == [], f"綺麗な本は defect 無し (got {clean['defects']})")
    check(0 <= clean["layers"]["l1_bib"] <= 1, "l1 は 0–1")
    # 汚い本の defect とルート
    check(any(d.startswith("L1:") for d in dirty["defects"]), "汚い本に L1 defect")
    check(any(d.startswith("L3:") for d in dirty["defects"]), "汚い本に L3 defect")
    check("repair_hints" in dirty and dirty["repair_hints"], "修復ヒントあり")
    # 単一ソースは edition insufficient → edition_unresolved defect
    check("L3:edition_unresolved" in dirty["defects"], "単一ソースは版未解決")
    # DDSELFHEAL must_fix #4: health と apply_eligibility は別軸。
    check(clean["apply_eligible"] is True and clean["apply_blockers"] == [],
          "綺麗な本は apply 適格・P0 ブロッカー無し")
    check(dirty["apply_eligible"] is False and "edition_unresolved" in dirty["apply_blockers"],
          "汚い本は P0 で apply 不適格 (版未解決)")
    check(clean["clean"] is True and dirty["clean"] is False, "clean フラグ")
    check("clean_reason" in clean and "clean_reason" in dirty, "clean 理由を提示")


def test_corpus_health() -> None:
    res = corpus_health([_clean_book(), _dirty_book()])
    check(res["books"] == 2, "2冊集計")
    check(res["report_only"] is True, "report-only")
    check(res["clean_count"] == 1, "clean は1冊")
    check(res["min_health"] <= res["mean_health"], "min <= mean")
    check(sum(res["buckets"].values()) == 2, "bucket 合計=2")
    # DDSELFHEAL must_fix #4/#5: apply 適格と quarantine KPI を別軸で出す。
    check(res["apply_eligible_count"] == 1, "apply 適格は1冊 (汚い本は P0 で除外)")
    check("quarantine" in res and "rate" in res["quarantine"], "quarantine KPI あり")
    check(res["quarantine"]["needs_ledger"], "履歴 ledger 要の KPI を明示")
    check(isinstance(res["defect_counts"], dict) and res["defect_counts"], "defect 分布あり")


def _year_gap1_book() -> dict:
    # 核タイトル一致・版表記なし・年差1。v1=別版疑い / v2=同一 (年差±1許容) に割れる本。
    return {
        "isbn": "9784000000200", "title": "民法総則",
        "source_meta": {
            "legallib": {"isbn": "9784000000200", "title": "民法総則", "publisher": "Z",
                         "year": "2020", "page_count": 300, "page_basis": "print_page"},
            "bencom": {"isbn": "9784000000200", "title": "民法総則", "publisher": "Z",
                       "year": "2021", "page_count": 300, "page_basis": "print_page"}},
        "sources": {
            "legallib": [{"title": "第1章 通則", "depth": 1}, {"title": "第2章 人", "depth": 1}],
            "bencom": [{"title": "第1章 通則", "depth": 1}, {"title": "第2章 人", "depth": 1}]},
    }


def test_v2_flip_end_to_end() -> None:
    # 既定 (v1) は別版疑い、thresholds で v2 に切替えると同一解決 → flip が配線されている。
    book = _year_gap1_book()
    v1 = book_summary(book["isbn"], book["title"], book["sources"], book["source_meta"],
                      load_thresholds())  # 既定 v1
    v2 = book_summary(book["isbn"], book["title"], book["sources"], book["source_meta"],
                      load_thresholds(override={"edition_classifier_version": "v2"}))
    check(v1["edition_identity_status"] == "suspected_different_manifestation",
          f"v1 は年差1で別版疑い (got {v1['edition_identity_status']})")
    check(v2["edition_identity_status"] == "resolved_same_manifestation",
          f"v2 は年差±1許容で同一解決 (got {v2['edition_identity_status']})")
    # flip により risk も改善 (high -> low)。
    check(v1["risk"] == "high" and v2["risk"] == "low", "v2 切替で risk 改善")


def test_corpus_health_ledger_wired() -> None:
    """ledger_path を渡すと quarantine KPI が needs_ledger から実値に置き換わる。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from quarantine_ledger import ENTER, QuarantineLedger
    books = [{"isbn": "9784000000020", "title": "民法",
              "source_meta": {"legallib": {"isbn": "9784000000020", "title": "民法",
                                           "page_basis": "print_page", "source_sha256": "sha256:x"}},
              "sources": {"legallib": [{"title": "第1章", "title_norm": "第1章",
                                        "depth": 1, "print_page": 1}]}}]
    # ledger 無し: 従来どおり needs_ledger。
    ch0 = corpus_health(books)
    check("needs_ledger" in ch0["quarantine"], "ledger 無しは needs_ledger を立てる")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "q.jsonl"
        n = [0.0]

        def clk():
            v = n[0]
            n[0] += 86400.0
            return v
        lg = QuarantineLedger(p, clock=clk)
        lg.record(isbn="A", locator="x#0", transition=ENTER, reason_code="orphan", decided_by="e")
        lg.record(isbn="A", locator="x#1", transition=ENTER, reason_code="orphan", decided_by="e")
        ch = corpus_health(books, ledger_path=p, ledger_now=5 * 86400.0)
        q = ch["quarantine"]
        check("needs_ledger" not in q, "ledger 有りは needs_ledger を消す")
        check(q["ledger_open_count"] == 2, f"open=2 (実 {q.get('ledger_open_count')})")
        check(q["max_age_days"] == 5.0, f"max_age=5 (実 {q.get('max_age_days')})")
        check(q["escape_rate"] == 0.0 and q["recurrence_rate"] == 0.0, "escape/recur=0")
        check(q["ledger_chain_ok"], "ledger chain OK")


def main() -> int:
    for t in [test_thresholds, test_book_health, test_corpus_health,
              test_corpus_health_ledger_wired, test_v2_flip_end_to_end]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
