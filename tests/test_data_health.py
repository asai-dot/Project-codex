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


def test_corpus_health() -> None:
    res = corpus_health([_clean_book(), _dirty_book()])
    check(res["books"] == 2, "2冊集計")
    check(res["report_only"] is True, "report-only")
    check(res["clean_count"] == 1, "clean は1冊")
    check(res["min_health"] <= res["mean_health"], "min <= mean")
    check(sum(res["buckets"].values()) == 2, "bucket 合計=2")


def main() -> int:
    for t in [test_thresholds, test_book_health, test_corpus_health]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
